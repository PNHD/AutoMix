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
low-pass filter and can alias for large instantaneous rate changes). For
the SMALL corrections this project's fixtures ever require (<=6% deviation,
PM's own conditional-quality ceiling), this is a reasonable, bounded-risk
choice for a P0 prototype; a production implementation would likely want
band-limited interpolation. `discontinuity_proxy` is run on the ramped
output as a machine sanity check, and the result is reported honestly,
not asserted safe by construction.
"""
from __future__ import annotations

import numpy as np


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
