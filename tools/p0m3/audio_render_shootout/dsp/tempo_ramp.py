"""
MATCH_AND_RETURN_TO_NATIVE ramp prototype (PM OWNER LISTENING DIRECTION
UPDATE, Task 2 "TEMPO-RAMP RESULTS").

After the crossfade overlap completes, the incoming track is already
playing at the MATCHED tempo (Signalsmith's `rate` parameter applied for
the whole M2 stretch job). This module smoothly brings its LOCAL playback
rate back toward 1.0x-of-its-own-matched-self == native tempo, over a
bounded settling region, via a single continuous sample-domain warp (not
block-spliced OLA, so there is no seam/discontinuity between ramp
segments by construction): for every output sample, an instantaneous
rate `r(t)` (smoothstep-interpolated, monotonic, C1-continuous at both
ends) determines how fast the already-matched buffer's own timeline is
consumed; the output is produced by linear interpolation at the resulting
continuously-varying input position. This is a deterministic, documented,
from-scratch resample (no external engine, no GPL/Signalsmith code) --
NOT a second call into the pinned Signalsmith/Rubber Band engines.

Honest limitation: linear-interpolation resampling is lower fidelity than
a proper windowed-sinc or phase-vocoder resampler (it acts as a mild
low-pass filter and can alias for large instantaneous rate changes).
`discontinuity_proxy` is run on the ramped output as a machine sanity
check, and the result is reported honestly, not asserted safe by
construction.

PM REVIEW "PRE-REAL-MUSIC REPAIR REQUIRED" R1: independent PM measurement
proved this is NOT pitch-preserving -- resampling a buffer's own timeline
at a rate `r != 1.0` shifts its pitch by `1200*log2(r)` cents, which is
exactly ordinary varispeed, not time-stretch. For `matched_rate=1.05`
(`to_rate=1/1.05=0.952381`) PM measured ~-85 cents drift on a 440Hz test
tone; `measure_ramp_pitch_drift_cents`/`ramp_is_safe` below reproduce that
measurement deterministically and are the real gate `dsp.tempo_modes`
consumes -- no caller may claim "safe" without actually running it.
`ramp_is_safe` is expected to return `False` for every deviation this
project's tempo envelope ever authorizes (0-12%, see
`tools/p0m3/transition_policy/policy/compatibility.py`
`MAX_JUSTIFIED_TEMPO_STRETCH_PCT`) with the CURRENT linear-resample
implementation -- that is the correct, honest outcome, not a bug in the
gate. A real pitch-preserving return-to-native path would need to run the
already-approved variable-rate stretch engine (Signalsmith) over the
settling region instead of this from-scratch resampler; that is explicitly
out of scope for this repair pass (PM: "Do NOT replace the current
resampler with another ordinary resampler; ordinary playback-rate change
still changes pitch" / "must be separately validated before reenabling").
"""
from __future__ import annotations

import numpy as np

# PROJECT diagnostic tolerance (PM REVIEW R1 "small explicitly documented
# PROJECT diagnostic tolerance") -- NOT a claim about human just-noticeable-
# difference thresholds (commonly cited in the 5-25 cent range depending on
# timbre/training); chosen conservatively small so this gate only ever
# passes for a return-to-native implementation that is genuinely,
# measurably pitch-preserving, not merely "close enough to sound okay".
PITCH_DRIFT_TOLERANCE_CENTS = 5.0

# Fixed, documented test parameters for the deterministic sinusoid-based
# gate check (PM REVIEW R1 "Add a deterministic pitch-preservation verifier
# using known sinusoidal/harmonic material"). The final held-region pitch
# produced by `apply_return_to_native_ramp` depends only on `matched_rate`
# (the ramp reaches a constant rate `1/matched_rate` and holds there), not
# on `sr`/duration/test frequency, so any fixed, adequately-long probe tone
# is a faithful, reproducible measurement.
PITCH_TEST_SR = 44100
PITCH_TEST_FREQ_HZ = 440.0
PITCH_TEST_TOTAL_S = 3.0
PITCH_TEST_RAMP_DURATION_S = 1.0
PITCH_TEST_HOLD_MEASURE_S = 1.0  # window measured well after the ramp settles


def _estimate_dominant_freq_hz(x: np.ndarray, sr: int) -> float:
    """
    Parabolic-interpolated FFT peak frequency estimate for a single-tone
    probe signal -- standard, public-domain technique (quadratic
    interpolation of the log-magnitude spectrum around the coarse peak
    bin), adequate precision (~sub-cent) for a stationary sinusoid held
    over >= 1 second at a 44.1kHz rate.
    """
    n = x.shape[0]
    if n < 4:
        return float("nan")
    windowed = x * np.hanning(n)
    spectrum = np.fft.rfft(windowed)
    mag = np.abs(spectrum)
    mag[0] = 0.0  # ignore DC
    k = int(np.argmax(mag))
    if k <= 0 or k >= len(mag) - 1:
        return k * sr / n
    a, b, c = mag[k - 1], mag[k], mag[k + 1]
    denom = (a - 2.0 * b + c)
    delta = 0.5 * (a - c) / denom if denom != 0 else 0.0
    return (k + delta) * sr / n


def measure_ramp_pitch_drift_cents(
    matched_rate: float,
    sr: int = PITCH_TEST_SR,
    test_freq_hz: float = PITCH_TEST_FREQ_HZ,
    ramp_duration_s: float = PITCH_TEST_RAMP_DURATION_S,
) -> dict:
    """
    Runs `apply_return_to_native_ramp` on a known mono sine tone at
    `test_freq_hz` and measures the dominant frequency in a window fully
    inside the POST-ramp held region, i.e. after the ramp has finished
    settling toward native tempo. Since a correct return-to-native
    implementation should return the incoming content to its own
    original, unshifted pitch, `test_freq_hz` doubles as both the input
    tone AND the expected/ground-truth output pitch. Returns a dict with
    `measured_freq_hz`, `expected_freq_hz`, `cents_drift`, `safe`
    (bool, `abs(cents_drift) <= PITCH_DRIFT_TOLERANCE_CENTS`).
    """
    n_total = int(round(PITCH_TEST_TOTAL_S * sr))
    t = np.arange(n_total) / sr
    tone = np.sin(2.0 * np.pi * test_freq_hz * t).astype(np.float64)
    matched_audio = np.stack([tone, tone], axis=1)

    ramped, _rate_curve = apply_return_to_native_ramp(
        matched_audio, sr, matched_rate, ramp_duration_s, hold_before_ramp_s=0.0
    )

    measure_len = int(round(PITCH_TEST_HOLD_MEASURE_S * sr))
    hold_start = ramped.shape[0] - measure_len
    if hold_start < 0:
        return {
            "measured_freq_hz": None,
            "expected_freq_hz": test_freq_hz,
            "cents_drift": None,
            "safe": False,
            "reason": "ramped output too short to measure a stable post-ramp hold window",
        }
    hold_window = ramped[hold_start:hold_start + measure_len, 0]
    measured_freq = _estimate_dominant_freq_hz(hold_window, sr)
    cents_drift = 1200.0 * float(np.log2(measured_freq / test_freq_hz)) if measured_freq > 0 else float("nan")
    safe = bool(np.isfinite(cents_drift) and abs(cents_drift) <= PITCH_DRIFT_TOLERANCE_CENTS)
    return {
        "measured_freq_hz": round(float(measured_freq), 3),
        "expected_freq_hz": test_freq_hz,
        "cents_drift": round(cents_drift, 2) if np.isfinite(cents_drift) else None,
        "tolerance_cents": PITCH_DRIFT_TOLERANCE_CENTS,
        "safe": safe,
    }


def ramp_is_safe(matched_rate: float) -> tuple[bool, dict]:
    """
    The REAL gate `dsp.tempo_modes.select_tempo_mode` consumes before it
    may ever return `MATCH_AND_RETURN_TO_NATIVE` (PM REVIEW R1: "the
    current documentation also says MATCH_AND_RETURN_TO_NATIVE is
    selected only if dsp.tempo_ramp.ramp_is_safe passes, but no such
    function exists" -- this makes that claim true). Runs the
    deterministic sinusoid pitch-drift measurement above at the exact
    `matched_rate` a caller would apply and returns
    `(is_safe, evidence_dict)`. Exact match (`matched_rate == 1.0`, no
    correction to ramp back from) is trivially safe.
    """
    if abs(matched_rate - 1.0) < 1e-9:
        return True, {"measured_freq_hz": PITCH_TEST_FREQ_HZ, "expected_freq_hz": PITCH_TEST_FREQ_HZ, "cents_drift": 0.0, "tolerance_cents": PITCH_DRIFT_TOLERANCE_CENTS, "safe": True, "reason": "matched_rate == 1.0, no ramp to evaluate"}
    evidence = measure_ramp_pitch_drift_cents(matched_rate)
    return bool(evidence.get("safe", False)), evidence


def _smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def apply_return_to_native_ramp(
    matched_audio: np.ndarray,
    sr: int,
    matched_rate: float,
    ramp_duration_s: float,
    hold_before_ramp_s: float = 0.0,
) -> tuple[np.ndarray, list[dict]]:
    """
    `matched_audio`: incoming content already stretched to the matched
    tempo (i.e. this is the M2 post-roll buffer, already at
    `required_tempo_ratio`). `matched_rate`: that same ratio (e.g. 1.05).
    Returns (ramped_audio, rate_curve) where rate_curve is a list of
    `{t_ms, instantaneous_rate_relative_to_matched, cumulative_input_sample}`
    sampled every 100ms, and `instantaneous_rate_relative_to_matched` goes
    from `1.0` (still exactly matched, no change) to `1.0/matched_rate`
    (fully back to native tempo relative to the matched buffer) via a
    smoothstep, then holds at native for the remainder.
    """
    n_in = matched_audio.shape[0]
    n_ch = matched_audio.shape[1]
    to_rate = 1.0 / matched_rate

    # Generous output-length estimate (bounded by input exhaustion below).
    avg_rate = (1.0 + to_rate) / 2.0
    max_out = int(n_in / max(avg_rate, 1e-6) * 1.15) + sr

    t = np.arange(max_out) / sr
    progress = _smoothstep((t - hold_before_ramp_s) / max(ramp_duration_s, 1e-9))
    r = 1.0 + (to_rate - 1.0) * progress  # 1.0 -> to_rate, smoothstep

    input_pos = np.cumsum(r)  # cumulative "input samples consumed" per output sample
    valid = input_pos < (n_in - 1)
    n_out = int(np.sum(valid))
    if n_out <= 0:
        return np.zeros((0, n_ch), dtype=matched_audio.dtype), []
    input_pos = input_pos[:n_out]
    r = r[:n_out]
    t = t[:n_out]

    idx0 = np.floor(input_pos).astype(np.int64)
    frac = (input_pos - idx0)[:, None]
    idx1 = np.minimum(idx0 + 1, n_in - 1)
    out = matched_audio[idx0] * (1.0 - frac) + matched_audio[idx1] * frac
    out = out.astype(matched_audio.dtype)

    stride = max(1, int(round(0.1 * sr)))  # report the curve every ~100ms
    rate_curve = [
        {
            "t_ms": round(float(t[i]) * 1000.0, 1),
            "instantaneous_rate_relative_to_matched": round(float(r[i]), 6),
            "cumulative_input_sample": int(input_pos[i]),
        }
        for i in range(0, n_out, stride)
    ]
    return out, rate_curve
