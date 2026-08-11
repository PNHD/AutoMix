"""
Normalized comparison shape every candidate/baseline runner in this
disposable harness must emit (Issue #5 Task B). Fields that a given
candidate does not produce are left as None/"UNKNOWN" -- never fabricated.

This is a harness-local schema for P0-M3-R1 analyzer comparison output.
It is intentionally distinct from (and not a replacement for)
docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md, which governs transition
-pair benchmark fixtures, not raw analyzer output.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Any


@dataclass
class AnalyzerResult:
    candidate_id: str                       # e.g. "beatnet", "scalar_bpm_baseline"
    candidate_kind: str                     # "ML_MODEL" | "BASELINE" | "REFERENCE_ORACLE"
    fixture_id: str
    run_state: str                          # "OK" | "FAILED" | "BLOCKED_ENVIRONMENT" | "BLOCKED_LICENSE" | "SOURCE_ONLY_INSPECTED"
    error: Optional[str] = None

    # --- core analysis fields (Issue #5 Task B normalized shape) ---
    bpm: Optional[float] = None
    bpm_confidence: Optional[float] = None
    beat_timestamps_ms: Optional[list[float]] = None
    beat_confidence: Optional[float] = None
    downbeat_timestamps_ms: Optional[list[float]] = None
    beat_position_in_bar: Optional[list[int]] = None      # 1-indexed position per beat, parallel to beat_timestamps_ms
    downbeat_confidence: Optional[float] = None
    meter_numerator: Optional[int] = None
    meter_denominator: Optional[int] = None
    meter_confidence: Optional[float] = None

    # cue_points_ms is the VALIDATED array, clamped to [0, track_duration_ms]
    # (PM REPAIR R5/R10). raw_cue_points_ms preserves the model's literal
    # unvalidated output (may contain negative/out-of-range values) so
    # invalid predictions stay auditable rather than silently vanishing.
    cue_points_ms: Optional[list[float]] = None
    raw_cue_points_ms: Optional[list[float]] = None
    n_invalid_cue_predictions: Optional[int] = None
    invalid_cue_points_raw_ms: Optional[list[float]] = None  # the raw values that fell outside [0, duration_ms]
    # cue_score is a per-cue numeric score whose MEANING is declared by
    # cue_score_kind (e.g. "MINMAX_NORMALIZED_DETR_DETECTION_SCORE") -- never
    # implied to be a calibrated confidence unless it genuinely is one.
    # cue_confidence stays null/UNKNOWN unless a candidate emits an actually
    # calibrated musical-cue confidence (PM REPAIR R5/R9).
    cue_score: Optional[list[float]] = None                # parallel to cue_points_ms
    cue_score_kind: Optional[str] = None
    cue_confidence: Optional[list[float]] = None            # parallel to cue_points_ms; None unless calibrated

    phrase_boundaries_ms: Optional[list[float]] = None
    section_boundaries: Optional[list[dict]] = None        # [{"t_start_ms","t_end_ms","label"}]

    # --- runtime / portability fields (Issue #5 Task E, repaired per PM REPAIR R1) ---
    # run_phase distinguishes three genuinely different things that were
    # previously conflated under one boolean is_cold_run:
    #   "N_A"                      -- baselines: no model to load, phase concept doesn't apply
    #   "ASSET_FETCH"               -- network/disk download & deserialization of checkpoint/config
    #                                  weights, timed separately from inference (see
    #                                  asset_fetch_wall_sec below); not itself a run_phase value
    #                                  on a per-fixture AnalyzerResult, but its cost is folded into
    #                                  the first fixture's COLD_MODEL_LOAD_INFERENCE wall time and
    #                                  reported separately via asset_fetch_wall_sec on that record.
    #   "COLD_MODEL_LOAD_INFERENCE" -- estimator/model constructed (or first used) in THIS process
    #                                  for the first time, then ran inference on this fixture.
    #   "WARM_INFERENCE"            -- the SAME already-resident estimator/model object (verified,
    #                                  not assumed) was reused in-process for this fixture; wall
    #                                  time reflects inference only, no construction/reload.
    run_phase: Optional[str] = None
    asset_fetch_wall_sec: Optional[float] = None  # non-null only on the record whose run_phase is
                                                   # COLD_MODEL_LOAD_INFERENCE and that actually
                                                   # triggered the load in this process
    wall_time_sec: Optional[float] = None         # inference-only wall time (excludes asset_fetch_wall_sec)
    memory_measurement_method: Optional[str] = None  # "PSUTIL_PROCESS_PEAK_WSET_RSS" | "PYTHON_TRACEMALLOC_ONLY" | "N/A"
    process_peak_rss_mb: Optional[float] = None       # OS-level peak RSS (Windows: psutil peak_wset), when available
    python_tracemalloc_peak_mb: Optional[float] = None  # Python-object-level only; NEVER the true process peak
    device: Optional[str] = None            # "cpu" | "cuda:0" | "N/A"
    checkpoint_size_mb: Optional[float] = None               # the single primary model checkpoint asset
    total_model_asset_footprint_mb: Optional[float] = None   # checkpoint + every other model/backbone/config
                                                               # asset actually required at inference time

    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
