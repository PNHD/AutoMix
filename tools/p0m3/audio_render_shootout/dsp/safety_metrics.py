"""
Machine/diagnostic metrics for P0-M3-R3 (Issue #7 "OBJECTIVE / DIAGNOSTIC
METRICS"). Every function here is DIAGNOSTIC ONLY -- nothing in this module
computes or returns a subjective "seamless"/PASS verdict; see
docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md and AGENTS.md rule 2.

`loudness_proxy_dbfs` is an RMS-based short-term-loudness PROXY, explicitly
NOT a full ITU-R BS.1770 K-weighted LUFS implementation (that would require
a K-weighting pre-filter and gated integration this disposable harness does
not implement) -- labelled honestly so it is never mistaken for a calibrated
loudness measurement.
"""
from __future__ import annotations

import numpy as np


def nan_inf_count(x: np.ndarray) -> int:
    return int(np.count_nonzero(~np.isfinite(x)))


def peak_dbfs(x: np.ndarray) -> float:
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    return 20.0 * np.log10(peak) if peak > 0 else float("-inf")


def clipped_sample_count(x: np.ndarray, threshold: float = 0.999969) -> int:
    return int(np.count_nonzero(np.abs(x) >= threshold))


def discontinuity_proxy(x: np.ndarray, sr: int, jump_threshold_sigma: float = 8.0) -> dict:
    """
    A click/discontinuity PROXY: flags sample-to-sample jumps that are
    implausibly large relative to the LOCAL signal's typical sample-to-
    sample delta (a rolling-window robust z-score on the first difference).
    This is a heuristic proxy, not a perceptual click detector -- reported
    honestly as such; see AGENTS.md "AutoMix terminology gate"-adjacent
    discipline of not overclaiming precision.
    """
    if x.shape[0] < 3:
        return {"discontinuity_count": 0, "max_abs_delta": 0.0, "max_abs_delta_position_s": None}
    mono = x.mean(axis=1) if x.ndim == 2 else x
    delta = np.diff(mono)
    window = max(64, sr // 100)
    abs_delta = np.abs(delta)
    # Rolling median-absolute-deviation via a simple block-wise approach
    # (fast, adequate for a diagnostic proxy; avoids a slow per-sample
    # rolling-window implementation over multi-million-sample buffers).
    n_blocks = max(1, len(abs_delta) // window)
    trimmed = abs_delta[: n_blocks * window].reshape(n_blocks, window)
    block_median = np.median(trimmed, axis=1, keepdims=True)
    block_mad = np.median(np.abs(trimmed - block_median), axis=1, keepdims=True) + 1e-9
    z = np.abs(trimmed - block_median) / (1.4826 * block_mad)
    flagged = z > jump_threshold_sigma
    count = int(np.count_nonzero(flagged))
    max_idx = int(np.argmax(abs_delta)) if abs_delta.size else 0
    return {
        "discontinuity_count": count,
        "max_abs_delta": float(np.max(abs_delta)) if abs_delta.size else 0.0,
        "max_abs_delta_position_s": max_idx / sr,
    }


def discontinuity_proxy_at_edges(x: np.ndarray, sr: int, edge_samples: list[int], window_ms: float = 50.0, jump_threshold_sigma: float = 8.0) -> dict:
    """
    Same robust-z-score jump proxy as `discontinuity_proxy`, but scoped to
    small windows around specific SPLICE-CANDIDATE sample positions (Issue
    #7 "discontinuity/click proxy around transition edges"), rather than
    the whole clip. Scanning the whole clip flags ordinary drum/percussion
    transients as false positives (a kick or snare attack has a large,
    legitimate sample-to-sample jump); scoping to the actual splice points
    is what makes this a meaningful click-at-the-seam check.
    """
    mono = x.mean(axis=1) if x.ndim == 2 else x
    half_win = max(4, int(round(window_ms / 1000.0 * sr / 2)))
    per_edge = []
    for edge in edge_samples:
        lo = max(0, edge - half_win)
        hi = min(len(mono), edge + half_win)
        segment = mono[lo:hi]
        if segment.size < 3:
            per_edge.append({"edge_sample": edge, "discontinuity_count": 0, "max_abs_delta": 0.0})
            continue
        delta = np.abs(np.diff(segment))
        median = np.median(delta)
        mad = np.median(np.abs(delta - median)) + 1e-9
        z = np.abs(delta - median) / (1.4826 * mad)
        per_edge.append({
            "edge_sample": edge,
            "discontinuity_count": int(np.count_nonzero(z > jump_threshold_sigma)),
            "max_abs_delta": float(np.max(delta)),
        })
    return {
        "per_edge": per_edge,
        "total_discontinuity_count": sum(e["discontinuity_count"] for e in per_edge),
    }


def rms_dbfs(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if x.size else 0.0
    return 20.0 * np.log10(rms) if rms > 0 else float("-inf")


def loudness_proxy_dbfs(x: np.ndarray, sr: int, window_s: float = 0.4) -> np.ndarray:
    """Short-term RMS-based loudness PROXY (not calibrated LUFS) in dBFS, one value per window_s block."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    win = max(1, int(round(window_s * sr)))
    n_blocks = max(1, len(mono) // win)
    trimmed = mono[: n_blocks * win].reshape(n_blocks, win)
    rms = np.sqrt(np.mean(trimmed.astype(np.float64) ** 2, axis=1))
    return 20.0 * np.log10(np.maximum(rms, 1e-12))


def loudness_jump_at_handoff_db(x: np.ndarray, sr: int, handoff_sample: int, window_s: float = 0.4) -> float:
    """abs(loudness_proxy just before handoff - loudness_proxy just after handoff), in dB."""
    win = max(1, int(round(window_s * sr)))
    before = x[max(0, handoff_sample - win):handoff_sample]
    after = x[handoff_sample:handoff_sample + win]
    if before.size == 0 or after.size == 0:
        return 0.0
    return abs(rms_dbfs(before) - rms_dbfs(after))


def detect_marker(
    x: np.ndarray,
    sr: int,
    expected_sample: int,
    freq_hz: float,
    duration_s: float,
    search_window_ms: float = 300.0,
) -> dict:
    """
    Matched-filter detection of the synthetic alignment-marker tick
    (fixtures/synth.py's high-frequency blip, embedded at an EXACTLY known
    sample position at authoring time) within a search window around the
    expected post-render position. Returns the actual detected sample and
    the ms error against synthetic ground truth (Issue #7 "beat alignment
    error ms against synthetic ground truth").
    """
    mono = x.mean(axis=1) if x.ndim == 2 else x
    n_template = max(1, int(round(duration_s * sr)))
    tt = np.arange(n_template) / sr
    template = np.sin(2 * np.pi * freq_hz * tt) * np.exp(-tt * 3500.0)
    template = template / (np.linalg.norm(template) + 1e-12)

    half_window = int(round(search_window_ms / 1000.0 * sr))
    lo = max(0, expected_sample - half_window)
    hi = min(len(mono), expected_sample + half_window + n_template)
    segment = mono[lo:hi]
    if len(segment) < n_template:
        return {"detected": False, "expected_sample": expected_sample, "detected_sample": None, "error_ms": None, "correlation_peak": 0.0}

    # Cross-correlation via a plain sliding dot-product (search window is
    # small -- a few hundred ms -- so this is fast without needing FFT
    # convolution).
    n_positions = len(segment) - n_template + 1
    scores = np.empty(n_positions)
    seg_energy = np.convolve(segment.astype(np.float64) ** 2, np.ones(n_template), mode="valid")
    for i in range(n_positions):
        window = segment[i:i + n_template]
        norm = np.sqrt(seg_energy[i]) + 1e-12
        scores[i] = float(np.dot(window, template) / norm)
    best_idx = int(np.argmax(scores))
    detected_sample = lo + best_idx
    error_ms = (detected_sample - expected_sample) / sr * 1000.0
    return {
        "detected": bool(scores[best_idx] > 0.15),
        "expected_sample": expected_sample,
        "detected_sample": detected_sample,
        "error_ms": error_ms,
        "correlation_peak": float(scores[best_idx]),
    }
