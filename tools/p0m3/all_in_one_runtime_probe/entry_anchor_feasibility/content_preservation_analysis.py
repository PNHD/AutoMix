"""P0-M3-R3 RM014 incoming-entry anchor feasibility -- skipped-content
preservation diagnostic (Issue #7 PM comment id 5310893724).

RM014 ONLY. No render, no All-In-One rerun, no new ML model. Uses only
librosa/numpy/soundfile primitives already relied on by this repository's
accepted independent oracle (``wsl_bounded_audio_oracles.py`` /
``pair_stability/analyze_harmonic_sensitivity.py``): STFT-band energy,
HPSS harmonic/percussive decomposition, spectral centroid, onset detection.
None of these are a vocal-separation model or a new confidence threshold
wired into any production gate -- this script's classification field is a
diagnostic label only, never written back into compatibility.py,
contract.py, or select_real_music_pairs.py.

For each candidate boundary (plus the full unanimous-intro span, for
context), measures the [0 ms, candidate_ms) region against 1-second-binned
whole-track distributions of:
  * RMS / loudness
  * onset density (onsets per second)
  * a coarse "vocal-activity proxy": STFT energy fraction in the
    300-3400 Hz band (typical vocal fundamental+formant range) -- NOT a
    vocal detector/separator, a spectral-band energy heuristic only.
  * a coarse "bass/percussion-activity proxy": percussive-component RMS
    (librosa HPSS) plus <150 Hz sub-band RMS.
  * spectral centroid (timbral brightness proxy, already a standard
    librosa feature).

Classification (diagnostic only, not a new production gate) is by
percentile of the region's mean value within the whole-track per-bin
distribution for RMS and onset density jointly:
  * region 10th-percentile-or-below on BOTH RMS and onset density ->
    CLEAR_NON_MUSICAL_LEAD_IN
  * region below the track median on RMS or onset density ->
    LOW_INFORMATION_MUSICAL_INTRO
  * region at/above the track median on both ->
    MEANINGFUL_AUTHORED_MUSICAL_INTRO
  * any required feature missing/region too short -> EVIDENCE_INSUFFICIENT
Active musical content is never auto-labeled disposable: the low-percentile
gate for CLEAR_NON_MUSICAL_LEAD_IN requires BOTH RMS and onset density to be
near-silent, not just one.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PureWindowsPath

import librosa
import numpy as np
import soundfile as sf

OPAQUE_ID = re.compile(r"^RM\d{3}$")
TRACK = "RM014"
ANALYSIS_SR = 44_100
FEATURE_SR = 22_050
HOP = 512
BIN_S = 1.0
VOCAL_BAND_HZ = (300.0, 3400.0)
SUB_BASS_BAND_HZ = (20.0, 150.0)


def windows_to_wsl(value: str) -> Path:
    if re.match(r"^[A-Za-z]:[\\/]", value):
        path = PureWindowsPath(value)
        drive = path.drive.rstrip(":").lower()
        return Path("/mnt") / drive / Path(*path.parts[1:])
    return Path(value)


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1, dtype=np.float32)
    if sr != ANALYSIS_SR:
        mono = librosa.resample(mono, orig_sr=sr, target_sr=ANALYSIS_SR, res_type="soxr_hq")
        sr = ANALYSIS_SR
    return np.asarray(mono, dtype=np.float32), sr


def band_energy_fraction(y: np.ndarray, sr: int, band_hz: tuple[float, float]) -> np.ndarray:
    stft = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    band_mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    total = np.sum(stft, axis=0)
    band = np.sum(stft[band_mask, :], axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.where(total > 1e-12, band / total, 0.0)
    times = librosa.frames_to_time(np.arange(stft.shape[1]), sr=sr, hop_length=HOP)
    return times, frac


def compute_whole_track_bins(y: np.ndarray, sr: int) -> dict:
    duration_s = len(y) / sr
    n_bins = int(np.ceil(duration_s / BIN_S))

    rms_times = librosa.frames_to_time(
        np.arange(len(librosa.feature.rms(y=y, hop_length=HOP)[0])), sr=sr, hop_length=HOP
    )
    rms_vals = librosa.feature.rms(y=y, hop_length=HOP)[0]

    onset_times = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP, units="time")

    centroid_vals = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP)[0]
    centroid_times = librosa.frames_to_time(np.arange(len(centroid_vals)), sr=sr, hop_length=HOP)

    vocal_times, vocal_frac = band_energy_fraction(y, sr, VOCAL_BAND_HZ)
    sub_times, sub_frac = band_energy_fraction(y, sr, SUB_BASS_BAND_HZ)

    harmonic, percussive = librosa.effects.hpss(y)
    perc_rms_vals = librosa.feature.rms(y=percussive, hop_length=HOP)[0]
    perc_rms_times = librosa.frames_to_time(np.arange(len(perc_rms_vals)), sr=sr, hop_length=HOP)

    def bin_series(times: np.ndarray, values: np.ndarray) -> np.ndarray:
        out = np.zeros(n_bins)
        for b in range(n_bins):
            t0, t1 = b * BIN_S, (b + 1) * BIN_S
            mask = (times >= t0) & (times < t1)
            out[b] = float(np.mean(values[mask])) if np.any(mask) else 0.0
        return out

    onset_counts = np.zeros(n_bins)
    for t in onset_times:
        b = int(t // BIN_S)
        if 0 <= b < n_bins:
            onset_counts[b] += 1
    onset_density_per_s = onset_counts / BIN_S

    return {
        "duration_s": round(duration_s, 3),
        "n_bins": n_bins,
        "bin_seconds": BIN_S,
        "rms": bin_series(rms_times, rms_vals),
        "onset_density_per_s": onset_density_per_s,
        "vocal_band_energy_fraction": bin_series(vocal_times, vocal_frac),
        "sub_bass_energy_fraction": bin_series(sub_times, sub_frac),
        "percussive_rms": bin_series(perc_rms_times, perc_rms_vals),
        "spectral_centroid_hz": bin_series(centroid_times, centroid_vals),
    }


def percentile_of(value: float, distribution: np.ndarray) -> float:
    if len(distribution) == 0:
        return float("nan")
    return float(round(100.0 * np.mean(distribution <= value), 2))


def region_stats(bins: dict, start_ms: float, end_ms: float) -> dict:
    start_bin = int(start_ms / 1000.0 // BIN_S)
    end_bin = int(np.ceil(end_ms / 1000.0 / BIN_S))
    end_bin = min(end_bin, bins["n_bins"])
    if end_bin <= start_bin:
        return {"status": "EVIDENCE_INSUFFICIENT", "reason": "REGION_TOO_SHORT_FOR_ONE_BIN"}

    def region_mean(key: str) -> float:
        return float(np.mean(bins[key][start_bin:end_bin]))

    metrics = {
        "rms_mean": region_mean("rms"),
        "onset_density_per_s_mean": region_mean("onset_density_per_s"),
        "vocal_band_energy_fraction_mean": region_mean("vocal_band_energy_fraction"),
        "sub_bass_energy_fraction_mean": region_mean("sub_bass_energy_fraction"),
        "percussive_rms_mean": region_mean("percussive_rms"),
        "spectral_centroid_hz_mean": region_mean("spectral_centroid_hz"),
    }
    percentiles = {
        "rms_percentile_in_track": percentile_of(metrics["rms_mean"], bins["rms"]),
        "onset_density_percentile_in_track": percentile_of(metrics["onset_density_per_s_mean"], bins["onset_density_per_s"]),
        "vocal_band_energy_fraction_percentile_in_track": percentile_of(metrics["vocal_band_energy_fraction_mean"], bins["vocal_band_energy_fraction"]),
        "sub_bass_energy_fraction_percentile_in_track": percentile_of(metrics["sub_bass_energy_fraction_mean"], bins["sub_bass_energy_fraction"]),
        "percussive_rms_percentile_in_track": percentile_of(metrics["percussive_rms_mean"], bins["percussive_rms"]),
    }

    rms_p = percentiles["rms_percentile_in_track"]
    onset_p = percentiles["onset_density_percentile_in_track"]
    if rms_p <= 10.0 and onset_p <= 10.0:
        classification = "CLEAR_NON_MUSICAL_LEAD_IN"
    elif rms_p < 50.0 or onset_p < 50.0:
        classification = "LOW_INFORMATION_MUSICAL_INTRO"
    else:
        classification = "MEANINGFUL_AUTHORED_MUSICAL_INTRO"

    return {
        "status": "MEASURED",
        "start_ms": start_ms,
        "end_ms": end_ms,
        "duration_skipped_ms": round(end_ms - start_ms, 1),
        "n_bins_covered": end_bin - start_bin,
        "region_metrics": {k: round(v, 6) for k, v in metrics.items()},
        "region_metric_percentiles_in_whole_track": percentiles,
        "classification": classification,
        "classification_methodology": (
            "CLEAR_NON_MUSICAL_LEAD_IN requires BOTH rms and onset-density region "
            "means at or below the 10th percentile of their own whole-track "
            "per-1s-bin distribution (near-silent AND no attacks); "
            "LOW_INFORMATION_MUSICAL_INTRO requires either metric below the "
            "track median; otherwise MEANINGFUL_AUTHORED_MUSICAL_INTRO. "
            "Diagnostic label only -- not wired into any production gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--intro-clusters", required=True)
    parser.add_argument("--current-entry-ms", type=float, default=0.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    if TRACK not in mapping:
        raise ValueError("OPAQUE_ID_MISSING_FROM_APPROVED_MAPPING")

    clusters = json.loads(Path(args.intro_clusters).read_text(encoding="utf-8"))
    top_candidates = clusters["clusters_ranked"][:2]
    intro_end_ms = clusters["intro_interval"]["interval_end_ms"]

    y, sr = load_audio(windows_to_wsl(str(mapping[TRACK])))
    bins = compute_whole_track_bins(y, sr)

    regions = {}
    for c in top_candidates:
        key = f"rank{c['diagnostic_rank']}_center_{c['center_ms']}ms"
        regions[key] = {
            "candidate_center_ms": c["center_ms"],
            "candidate_diagnostic_rank": c["diagnostic_rank"],
            "candidate_support_count": c["support_count"],
            **region_stats(bins, args.current_entry_ms, c["center_ms"]),
        }
    regions["full_unanimous_intro_for_context"] = {
        "candidate_center_ms": intro_end_ms,
        **region_stats(bins, args.current_entry_ms, intro_end_ms),
    }

    output = {
        "schema_version": 1,
        "scope": "RM014 ONLY; diagnostic content-preservation measurement; no render, no All-In-One rerun",
        "track": TRACK,
        "whole_track_duration_s": bins["duration_s"],
        "bin_seconds": BIN_S,
        "current_canonical_entry_ms": args.current_entry_ms,
        "vocal_band_hz": list(VOCAL_BAND_HZ),
        "sub_bass_band_hz": list(SUB_BASS_BAND_HZ),
        "methodology_note": (
            "vocal-activity and bass/percussion 'activity' fields are spectral-band-energy "
            "and HPSS-percussive-RMS heuristics, not a vocal-separation model or dedicated "
            "drum/bass stem detector; reported as proxies only, matching this repository's "
            "existing structure/harmonic oracle honesty conventions."
        ),
        "regions": regions,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for key, r in regions.items():
        print(f"{key}: status={r.get('status')} classification={r.get('classification')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
