"""Bounded WSL benchmark oracles for Issue #7 analyzer-evidence recovery.

This worker is intentionally private-input/local-output.  Its job file may
contain owner-local paths and therefore must live under ``real_music/work_local``.
The output contains opaque RM IDs and analyzer measurements only; exceptions
are reduced to enumerated type names so a decoder/library error cannot leak a
private path.

The worker does not implement production analyzers:

* madmom RNN+DBN is ``BENCHMARK_ONLY`` downbeat/bar evidence;
* librosa CQT key estimation is an independent harmonic oracle;
* librosa beat-synchronous feature novelty is boundary evidence only.  It has
  no functional labels and must never be called phrase/outro recognition.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import re
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from madmom.features.downbeats import DBNDownBeatTrackingProcessor, RNNDownBeatProcessor
from scipy.signal import find_peaks

OPAQUE_ID_RE = re.compile(r"^RM\d{3}$")
ANALYSIS_SR = 44_100
FEATURE_SR = 22_050
HOP = 512
KEY_WINDOW_S = 30.0

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "UNKNOWN"


def load_audio(path: str) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1, dtype=np.float32)
    if sr != ANALYSIS_SR:
        mono = librosa.resample(mono, orig_sr=sr, target_sr=ANALYSIS_SR, res_type="soxr_hq")
        sr = ANALYSIS_SR
    return np.asarray(mono, dtype=np.float32), sr


def madmom_downbeats(y: np.ndarray) -> dict:
    activations = RNNDownBeatProcessor()(y)
    events = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)(activations)
    event_rows = [
        {"t_ms": round(float(t) * 1000.0, 1), "position_in_bar": int(pos)}
        for t, pos in events
    ]
    downbeats = [row for row in event_rows if row["position_in_bar"] == 1]
    strengths = []
    for row in downbeats:
        frame = min(max(int(round(row["t_ms"] / 10.0)), 0), len(activations) - 1)
        strengths.append(float(activations[frame, 1]))
    intervals = np.diff([row["t_ms"] for row in downbeats])
    interval_cv = float(np.std(intervals) / np.mean(intervals)) if len(intervals) >= 2 and np.mean(intervals) else None
    positions = sorted({row["position_in_bar"] for row in event_rows})
    inferred_meter = max(positions) if positions else None
    return {
        "source": "MADMOM_RNN_DOWNBEAT_PLUS_DBN_BENCHMARK_ONLY",
        "raw_evidence_type": "RNN_ACTIVATIONS_PLUS_DBN_SEQUENCE_NO_CALIBRATED_CONFIDENCE",
        "beat_events": event_rows,
        "downbeats_ms": [row["t_ms"] for row in downbeats],
        "inferred_meter": inferred_meter,
        "downbeat_count": len(downbeats),
        "median_downbeat_activation": round(float(np.median(strengths)), 6) if strengths else None,
        "downbeat_interval_cv": round(interval_cv, 6) if interval_cv is not None else None,
    }


def _profile_key(chroma: np.ndarray) -> dict:
    vector = np.mean(chroma, axis=1)
    total = float(np.sum(vector))
    if not math.isfinite(total) or total <= 1e-12:
        return {"root": None, "mode": None, "score": None, "margin": 0.0, "confidence": "NONE"}
    vector = vector / total
    scored = []
    for mode, profile in (("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)):
        for root in range(12):
            rolled = np.roll(profile, root)
            score = float(np.corrcoef(vector, rolled)[0, 1])
            scored.append((score, root, mode))
    scored.sort(reverse=True)
    best, second = scored[0], scored[1]
    margin = best[0] - second[0]
    confidence = "HIGH" if margin >= 0.08 else "MEDIUM" if margin >= 0.04 else "LOW"
    return {
        "root": PITCH_CLASSES[best[1]],
        "mode": best[2],
        "score": round(best[0], 6),
        "margin": round(margin, 6),
        "confidence": confidence,
    }


def cqt_key_at(y: np.ndarray, sr: int, center_ms: float, role: str) -> dict:
    if role == "exit":
        end = min(len(y), int(round(center_ms / 1000.0 * sr)))
        start = max(0, end - int(KEY_WINDOW_S * sr))
    else:
        start = min(len(y), int(round(center_ms / 1000.0 * sr)))
        end = min(len(y), start + int(KEY_WINDOW_S * sr))
    window = y[start:end]
    if len(window) < sr * 4:
        return {"source": "LIBROSA_CQT_KRUMHANSL_BENCHMARK_ONLY", "status": "STILL_UNKNOWN_SHORT_WINDOW", "estimate": _profile_key(np.zeros((12, 1)))}
    feature_y = librosa.resample(window, orig_sr=sr, target_sr=FEATURE_SR, res_type="soxr_hq")
    harmonic = librosa.effects.harmonic(feature_y)
    chroma = librosa.feature.chroma_cqt(y=harmonic, sr=FEATURE_SR, hop_length=HOP)
    return {
        "source": "LIBROSA_CQT_KRUMHANSL_BENCHMARK_ONLY",
        "status": "MEASURED",
        "window_start_ms": round(start / sr * 1000.0, 1),
        "window_end_ms": round(end / sr * 1000.0, 1),
        "estimate": _profile_key(chroma),
    }


def section_boundaries(y: np.ndarray, sr: int, beat_events: list[dict]) -> dict:
    """Audio-derived boundary candidates; deliberately no section labels."""
    feature_y = librosa.resample(y, orig_sr=sr, target_sr=FEATURE_SR, res_type="soxr_hq")
    chroma = librosa.feature.chroma_cqt(y=feature_y, sr=FEATURE_SR, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=feature_y, sr=FEATURE_SR, n_mfcc=13, hop_length=HOP)
    contrast = librosa.feature.spectral_contrast(y=feature_y, sr=FEATURE_SR, hop_length=HOP)
    features = np.vstack([chroma, mfcc, contrast])
    beat_times = np.array([row["t_ms"] / 1000.0 for row in beat_events], dtype=float)
    beat_frames = librosa.time_to_frames(beat_times, sr=FEATURE_SR, hop_length=HOP)
    beat_frames = np.unique(np.clip(beat_frames, 0, max(features.shape[1] - 1, 0)))
    if len(beat_frames) < 16:
        return {
            "source": "LIBROSA_BEAT_SYNCHRONOUS_CQT_MFCC_CONTRAST_CHANGEPOINT_BENCHMARK_ONLY",
            "status": "STILL_UNKNOWN_INSUFFICIENT_BEATS",
            "functional_labels_available": False,
            "boundary_candidates": [],
        }
    synced = librosa.util.sync(features, beat_frames, aggregate=np.median)
    synced = (synced - np.mean(synced, axis=1, keepdims=True)) / (np.std(synced, axis=1, keepdims=True) + 1e-8)
    novelty = np.linalg.norm(np.diff(synced, axis=1), axis=0)
    median = float(np.median(novelty))
    mad = float(np.median(np.abs(novelty - median))) + 1e-8
    novelty_z = (novelty - median) / (1.4826 * mad)
    peaks, props = find_peaks(novelty_z, height=1.5, distance=8)
    candidates = []
    for idx, z in zip(peaks, props.get("peak_heights", [])):
        beat_index = min(int(idx + 1), len(beat_times) - 1)
        candidates.append({"t_ms": round(float(beat_times[beat_index]) * 1000.0, 1), "prominence_z": round(float(z), 4)})
    return {
        "source": "LIBROSA_BEAT_SYNCHRONOUS_CQT_MFCC_CONTRAST_CHANGEPOINT_BENCHMARK_ONLY",
        "status": "BOUNDARY_EVIDENCE_ONLY_NO_FUNCTIONAL_LABELS" if candidates else "STILL_UNKNOWN_NO_BOUNDARIES",
        "functional_labels_available": False,
        "boundary_candidates": candidates,
    }


def analyze_track(job: dict) -> dict:
    opaque_id = job["opaque_id"]
    if not OPAQUE_ID_RE.fullmatch(opaque_id):
        raise ValueError("INVALID_OPAQUE_ID")
    y, sr = load_audio(job["private_path"])
    downbeat = madmom_downbeats(y)
    return {
        "opaque_id": opaque_id,
        "duration_ms": round(len(y) / sr * 1000.0, 1),
        "downbeat": downbeat,
        "structure": section_boundaries(y, sr, downbeat["beat_events"]),
        "harmonic": {
            "exit": cqt_key_at(y, sr, float(job["exit_candidate_t_ms"]), "exit"),
            "entry": cqt_key_at(y, sr, float(job["entry_candidate_t_ms"]), "entry"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    tracks = {}
    for item in job["tracks"]:
        opaque_id = item.get("opaque_id", "INVALID")
        try:
            tracks[opaque_id] = {"status": "OK", **analyze_track(item)}
        except Exception as exc:  # private-safe by construction: no str(exc)
            tracks[opaque_id] = {"status": "ERROR", "error_code": type(exc).__name__}
    output = {
        "schema_version": 1,
        "analyzer_versions": {
            "madmom": _version("madmom"),
            "librosa": _version("librosa"),
            "soundfile": _version("soundfile"),
            "numpy": _version("numpy"),
        },
        "tracks": tracks,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2), encoding="utf-8")
    ok = sum(1 for row in tracks.values() if row["status"] == "OK")
    print(f"BOUNDED_ORACLE_COMPLETE ok={ok} total={len(tracks)}")
    return 0 if ok == len(tracks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
