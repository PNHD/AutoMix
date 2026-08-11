"""
Negative baseline #3 (Issue #5 "REQUIRED NEGATIVE BASELINES"): simple
energy/onset candidate heuristic.

Pure numpy, no ML model, no GPL/AGPL source consulted or copied. Computes:
  - a short-window (50ms) RMS envelope -> local-maxima peak picking with a
    relative threshold and minimum separation, reported as "cue candidates"
    (this is exactly the kind of naive heuristic AutoMix must outperform,
    per AGENTS.md quality terminology: "BPM/key compatibility alone is
    never sufficient", extended here to "onset/energy peaks alone are not
    cue points").
  - a long-window (2s) RMS trend used to coarsely segment
    low-energy/high-energy regions, reported as section_boundaries (a weak
    proxy for structure, not a phrase/section model).

Independent implementation.
"""
from __future__ import annotations

import sys
import time
import wave

import numpy as np

sys.path.insert(0, "..")
from common.schema import AnalyzerResult  # noqa: E402


def _read_wav_mono_f64(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        raw = wf.readframes(n)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    return data, sr


def _rms_envelope(x: np.ndarray, sr: int, window_sec: float, hop_sec: float) -> tuple[np.ndarray, np.ndarray]:
    win = max(1, int(window_sec * sr))
    hop = max(1, int(hop_sec * sr))
    n_frames = max(0, (len(x) - win) // hop + 1)
    rms = np.zeros(n_frames)
    times = np.zeros(n_frames)
    for i in range(n_frames):
        s = i * hop
        seg = x[s:s + win]
        rms[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0
        times[i] = (s + win / 2) / sr
    return times, rms


def _peak_pick(times: np.ndarray, rms: np.ndarray, rel_threshold: float = 0.55,
               min_sep_sec: float = 1.0) -> list[float]:
    if len(rms) == 0:
        return []
    thresh = rel_threshold * float(np.max(rms))
    candidates = []
    last_t = -1e9
    for i in range(1, len(rms) - 1):
        if rms[i] >= thresh and rms[i] >= rms[i - 1] and rms[i] >= rms[i + 1]:
            if times[i] - last_t >= min_sep_sec:
                candidates.append(float(times[i]))
                last_t = times[i]
    return candidates


def _segment_by_energy(times: np.ndarray, rms: np.ndarray, n_levels: int = 3) -> list[dict]:
    if len(rms) == 0:
        return []
    lo, hi = float(np.min(rms)), float(np.max(rms))
    if hi <= lo:
        return [{"t_start_ms": 0, "t_end_ms": round(float(times[-1]) * 1000), "label": "other"}]
    edges = np.linspace(lo, hi, n_levels + 1)

    def level_of(v):
        for lvl in range(n_levels):
            if v <= edges[lvl + 1] or lvl == n_levels - 1:
                return lvl
        return n_levels - 1

    levels = [level_of(v) for v in rms]
    labels_by_level = {0: "low_energy", 1: "mid_energy", 2: "high_energy"}
    segments = []
    cur_level = levels[0]
    seg_start = times[0]
    for i in range(1, len(levels)):
        if levels[i] != cur_level:
            segments.append({
                "t_start_ms": round(float(seg_start) * 1000),
                "t_end_ms": round(float(times[i]) * 1000),
                "label": labels_by_level.get(cur_level, "other"),
            })
            cur_level = levels[i]
            seg_start = times[i]
    segments.append({
        "t_start_ms": round(float(seg_start) * 1000),
        "t_end_ms": round(float(times[-1]) * 1000),
        "label": labels_by_level.get(cur_level, "other"),
    })
    return segments


def run(fixture_id: str, wav_path: str) -> AnalyzerResult:
    t0 = time.perf_counter()
    result = AnalyzerResult(
        candidate_id="energy_onset_heuristic_baseline",
        candidate_kind="BASELINE",
        fixture_id=fixture_id,
        run_state="OK",
        notes="Negative baseline: RMS-envelope peak picking as 'cue candidates', "
              "coarse energy-level segmentation as a weak structure proxy. No beat/downbeat/"
              "phrase model of any kind.",
    )
    try:
        x, sr = _read_wav_mono_f64(wav_path)
        t_short, rms_short = _rms_envelope(x, sr, window_sec=0.05, hop_sec=0.01)
        cues = _peak_pick(t_short, rms_short)
        t_long, rms_long = _rms_envelope(x, sr, window_sec=2.0, hop_sec=0.5)
        segments = _segment_by_energy(t_long, rms_long)

        result.cue_points_ms = [round(c * 1000, 1) for c in cues]
        result.cue_confidence = None
        result.section_boundaries = segments
        result.device = "cpu"
    except Exception as exc:  # pragma: no cover - defensive, harness reports real failures
        result.run_state = "FAILED"
        result.error = f"{type(exc).__name__}: {exc}"
    result.estimator_lifecycle = "N_A"  # PM REPAIR R1/R8: no model to load; lifecycle concept doesn't apply
    result.memory_measurement_method = "N_A"
    result.total_call_wall_sec = time.perf_counter() - t0
    return result
