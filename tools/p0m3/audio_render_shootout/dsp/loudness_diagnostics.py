"""
Time-series loudness/energy continuity diagnostics (PM OWNER LISTENING
DIRECTION UPDATE -- "LOUDNESS / ENERGY CONTINUITY REPAIR").

The prior pass's `loudness_jump_at_handoff_db` (dsp/safety_metrics.py)
compared a single 400ms window immediately before a boundary sample
against a single 400ms window immediately after it. That is noisy by
construction for sparse, beat-synced percussive content: whether a kick/
snare/hat transient happens to fall just inside or just outside a single
400ms slice dominates the result far more than any real gain-curve
property, and it has no "reference" loudness to compare against, so a
single number can't distinguish "the mix dipped below normal" from "the
mix is naturally quieter here than some arbitrary nearby window."

This module instead produces a genuine short-window TIME SERIES (default
200ms windows, 100ms hop -- inside the PM-requested 100-250ms band) across
the whole transition region, anchored against a `pre_transition_reference_db`
measured over a longer, musically-stable window well before the
transition even starts (so transient noise averages out), and reports the
maximum dip/rise relative to that reference -- diagnostic only, never a
subjective pass/fail claim.
"""
from __future__ import annotations

import numpy as np

from dsp.mixing import split_bass

DEFAULT_WINDOW_MS = 200.0
DEFAULT_HOP_MS = 100.0
REFERENCE_WINDOW_S = 2.0  # length of the stable "before the transition" reference window
REFERENCE_LOOKBACK_S = 3.0  # how far before onset the reference window ends (avoids the immediate pre-onset region, which may itself already be affected by an authored outro/energy change)


def _rms_dbfs(x: np.ndarray) -> float:
    if x.size == 0:
        return float("-inf")
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    return 20.0 * np.log10(rms) if rms > 0 else float("-inf")


def windowed_loudness_curve(audio: np.ndarray, sr: int, start_smp: int, end_smp: int,
                             window_ms: float = DEFAULT_WINDOW_MS, hop_ms: float = DEFAULT_HOP_MS) -> list[dict]:
    """Short-window RMS-dBFS time series over [start_smp, end_smp), one entry per hop."""
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    win = max(1, int(round(window_ms / 1000.0 * sr)))
    hop = max(1, int(round(hop_ms / 1000.0 * sr)))
    start_smp = max(0, start_smp)
    end_smp = min(len(mono), end_smp)
    curve = []
    pos = start_smp
    while pos + win <= end_smp:
        segment = mono[pos:pos + win]
        curve.append({
            "t_ms": round((pos - start_smp) / sr * 1000.0, 1),
            "sample": pos,
            "db": round(_rms_dbfs(segment), 3),
        })
        pos += hop
    return curve


def compute_transition_loudness_diagnostics(
    audio: np.ndarray,
    sr: int,
    onset_render_smp: int,
    content_end_render_smp: int,
    analysis_pad_s: float = 3.0,
    window_ms: float = DEFAULT_WINDOW_MS,
    hop_ms: float = DEFAULT_HOP_MS,
) -> dict:
    """
    `onset_render_smp` / `content_end_render_smp`: the overlap window's
    start/end positions WITHIN THE FINAL RENDERED BUFFER (i.e.
    `pre_roll_len` and `pre_roll_len + overlap_len_samples` -- the same
    positions `dsp.safety_metrics.loudness_jump_at_handoff_db` used).

    Returns pre_transition_reference_db, local_loudness_curve,
    maximum_loudness_dip_db, maximum_loudness_rise_db,
    handoff_loudness_delta_db (at both overlap boundaries), bass_energy_curve.
    """
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio

    ref_end_smp = max(0, onset_render_smp - int(round(REFERENCE_LOOKBACK_S * sr)))
    ref_start_smp = max(0, ref_end_smp - int(round(REFERENCE_WINDOW_S * sr)))
    pre_transition_reference_db = _rms_dbfs(mono[ref_start_smp:ref_end_smp]) if ref_end_smp > ref_start_smp else _rms_dbfs(mono[:onset_render_smp])

    analysis_start = max(0, onset_render_smp - int(round(analysis_pad_s * sr)))
    analysis_end = min(len(mono), content_end_render_smp + int(round(analysis_pad_s * sr)))

    curve = windowed_loudness_curve(audio, sr, analysis_start, analysis_end, window_ms, hop_ms)
    transition_curve = [c for c in curve if onset_render_smp <= c["sample"] <= content_end_render_smp]

    finite_db = [c["db"] for c in transition_curve if np.isfinite(c["db"])]
    if finite_db and np.isfinite(pre_transition_reference_db):
        max_dip = max(0.0, pre_transition_reference_db - min(finite_db))
        max_rise = max(0.0, max(finite_db) - pre_transition_reference_db)
    else:
        max_dip = None
        max_rise = None

    def _handoff_delta(boundary_smp: int) -> float | None:
        half = int(round(200.0 / 1000.0 * sr))
        before = mono[max(0, boundary_smp - half):boundary_smp]
        after = mono[boundary_smp:boundary_smp + half]
        if before.size == 0 or after.size == 0:
            return None
        b, a = _rms_dbfs(before), _rms_dbfs(after)
        if not (np.isfinite(b) and np.isfinite(a)):
            return None
        return round(abs(a - b), 3)

    bass_band, _ = split_bass(audio, sr)
    bass_curve = windowed_loudness_curve(bass_band, sr, analysis_start, analysis_end, window_ms, hop_ms)

    return {
        "window_ms": window_ms,
        "hop_ms": hop_ms,
        "reference_window_s": REFERENCE_WINDOW_S,
        "reference_lookback_s": REFERENCE_LOOKBACK_S,
        "pre_transition_reference_db": round(pre_transition_reference_db, 3) if np.isfinite(pre_transition_reference_db) else None,
        "local_loudness_curve": curve,
        "maximum_loudness_dip_db": round(max_dip, 3) if max_dip is not None else None,
        "maximum_loudness_rise_db": round(max_rise, 3) if max_rise is not None else None,
        "handoff_loudness_delta_db_at_overlap_start": _handoff_delta(onset_render_smp),
        "handoff_loudness_delta_db_at_overlap_end": _handoff_delta(content_end_render_smp),
        "bass_energy_curve": bass_curve,
    }
