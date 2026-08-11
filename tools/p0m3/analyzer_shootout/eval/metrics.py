"""
Metrics computed against SYNTHETIC_EXACT ground truth, consistent with the
Condition Registry in docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md
Sec 7 (COND_BEAT_OK, COND_DOWNBEAT_OK, COND_PHRASE_OK, COND_SECTION_OK), reused
here for raw-analyzer evaluation rather than transition-pair evaluation.
"""
from __future__ import annotations

import math
from typing import Optional


def _nearest_distance(t: float, grid: list[float]) -> Optional[float]:
    if not grid:
        return None
    return min(abs(t - g) for g in grid)


def beat_alignment_errors_ms(pred_beats_ms: list[float], gt_beats_ms: list[float]) -> dict:
    """For each ground-truth beat, distance in ms to nearest predicted beat, and
    vice versa (to separately capture missed vs. extra events)."""
    if not pred_beats_ms:
        return {
            "median_gt_to_pred_ms": None, "mean_gt_to_pred_ms": None,
            "missed_beats": len(gt_beats_ms), "extra_beats": 0,
            "n_gt": len(gt_beats_ms), "n_pred": 0,
        }
    gt_to_pred = [_nearest_distance(t, pred_beats_ms) for t in gt_beats_ms]
    pred_to_gt = [_nearest_distance(t, gt_beats_ms) for t in pred_beats_ms]
    # A "missed" ground-truth beat = no predicted beat within 60ms; an "extra"
    # predicted beat = no ground-truth beat within 60ms. 60ms is a generous
    # coarse tolerance for event-existence counting; the beat-fraction
    # threshold below (COND_BEAT_OK, 1/16 beat) is the real acceptance test.
    tol_ms = 60.0
    missed = sum(1 for d in gt_to_pred if d > tol_ms)
    extra = sum(1 for d in pred_to_gt if d > tol_ms)
    return {
        "median_gt_to_pred_ms": sorted(gt_to_pred)[len(gt_to_pred) // 2],
        "mean_gt_to_pred_ms": sum(gt_to_pred) / len(gt_to_pred),
        "max_gt_to_pred_ms": max(gt_to_pred),
        "missed_beats": missed,
        "extra_beats": extra,
        "n_gt": len(gt_beats_ms),
        "n_pred": len(pred_beats_ms),
    }


def beat_alignment_fraction(pred_beats_ms: list[float], gt_beats_ms: list[float], beat_period_ms: float) -> dict:
    """COND_BEAT_OK: beat-alignment error as a fraction of the beat period,
    using the circular (wrap-aware) distance definition from benchmark
    contract Sec 8: min(|err|, period - |err|) / period."""
    if not pred_beats_ms or beat_period_ms <= 0:
        return {"median_beat_fraction_error": None, "cond_beat_ok_rate": None}
    fracs = []
    for t in gt_beats_ms:
        d = _nearest_distance(t, pred_beats_ms)
        if d is None:
            continue
        wrapped = min(d, beat_period_ms - d) if d < beat_period_ms else d
        fracs.append(wrapped / beat_period_ms)
    if not fracs:
        return {"median_beat_fraction_error": None, "cond_beat_ok_rate": None}
    ok = sum(1 for f in fracs if f <= (1.0 / 16.0))
    fracs_sorted = sorted(fracs)
    return {
        "median_beat_fraction_error": fracs_sorted[len(fracs_sorted) // 2],
        "cond_beat_ok_rate": ok / len(fracs),  # fraction of GT beats meeting COND_BEAT_OK (<=1/16 beat)
    }


def downbeat_bar_phase_error(pred_downbeats_ms: list[float], gt_downbeats_ms: list[float],
                              bar_period_ms: float) -> dict:
    """COND_DOWNBEAT_OK: bar-phase error must be exactly 0 beat positions.
    Here (raw analyzer, no beat-position array assumed) we measure whether
    each ground-truth downbeat has a predicted downbeat within a tight
    absolute tolerance (10% of the bar period), which is a necessary
    (not sufficient) proxy for exact bar-phase correctness at the raw-signal
    level; the exact discrete-position check is reserved for candidates that
    emit beat_position_in_bar (e.g. All-In-One)."""
    if not pred_downbeats_ms or bar_period_ms <= 0:
        return {"median_abs_error_ms": None, "within_10pct_bar_rate": None,
                "n_gt": len(gt_downbeats_ms), "n_pred": 0}
    errs = [_nearest_distance(t, pred_downbeats_ms) for t in gt_downbeats_ms]
    tol = 0.10 * bar_period_ms
    ok = sum(1 for e in errs if e <= tol)
    errs_sorted = sorted(errs)
    return {
        "median_abs_error_ms": errs_sorted[len(errs_sorted) // 2],
        "within_10pct_bar_rate": ok / len(errs),
        "n_gt": len(gt_downbeats_ms),
        "n_pred": len(pred_downbeats_ms),
    }


def exact_bar_phase_correctness(pred_beat_positions: list[int], gt_beats_ms: list[float],
                                 pred_beats_ms: list[float], beats_per_bar: int,
                                 gt_downbeat_indices: list[int]) -> dict:
    """Exact COND_DOWNBEAT_OK style check for candidates that emit an explicit
    beat_position_in_bar per predicted beat (e.g. All-In-One's beat_positions).
    Matches each ground-truth downbeat to the nearest predicted beat and
    checks the predicted bar-position label equals 1 (first position)."""
    if not pred_beat_positions or not pred_beats_ms:
        return {"exact_bar_phase_accuracy": None}
    correct = 0
    total = 0
    for gi in gt_downbeat_indices:
        gt_t = gt_beats_ms[gi]
        # nearest predicted beat index
        diffs = [abs(gt_t - pt) for pt in pred_beats_ms]
        nearest_i = diffs.index(min(diffs))
        total += 1
        if nearest_i < len(pred_beat_positions) and pred_beat_positions[nearest_i] == 1:
            correct += 1
    if total == 0:
        return {"exact_bar_phase_accuracy": None}
    return {"exact_bar_phase_accuracy": correct / total}


def phrase_section_boundary_distance_ms(pred_boundaries_ms: list[float], gt_boundaries_ms: list[float]) -> dict:
    if not pred_boundaries_ms or not gt_boundaries_ms:
        return {"median_abs_error_ms": None, "n_gt": len(gt_boundaries_ms), "n_pred": len(pred_boundaries_ms or [])}
    errs = [_nearest_distance(t, pred_boundaries_ms) for t in gt_boundaries_ms]
    errs_sorted = sorted(errs)
    return {
        "median_abs_error_ms": errs_sorted[len(errs_sorted) // 2],
        "max_abs_error_ms": max(errs),
        "n_gt": len(gt_boundaries_ms),
        "n_pred": len(pred_boundaries_ms),
    }


def bpm_error(pred_bpm: Optional[float], gt_bpm: float) -> dict:
    if pred_bpm is None or gt_bpm in (None, 0):
        return {"abs_error_bpm": None, "abs_error_pct": None, "half_double_time_note": None}
    abs_err = abs(pred_bpm - gt_bpm)
    note = None
    for factor, name in ((2.0, "double-time"), (0.5, "half-time")):
        if abs(pred_bpm - gt_bpm * factor) < abs_err:
            note = f"prediction closer to GT*{factor} ({name}) than to GT directly"
    return {
        "abs_error_bpm": round(abs_err, 3),
        "abs_error_pct": round(100.0 * abs_err / gt_bpm, 2),
        "half_double_time_note": note,
    }
