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

    # cue_points_ms is the VALIDATED array: raw predictions outside
    # [0, track_duration_ms] are FILTERED OUT (removed), never clamped
    # into range (PM REPAIR R5/R10 -- "filtered/validated", not "clamped",
    # matches what candidates/run_cuedetr.py actually does). raw_cue_points_ms
    # preserves the model's literal unvalidated output (may contain
    # negative/out-of-range values) and raw_cue_score preserves each raw
    # prediction's score in parallel, so every invalid prediction stays
    # fully auditable rather than silently vanishing.
    cue_points_ms: Optional[list[float]] = None
    raw_cue_points_ms: Optional[list[float]] = None
    raw_cue_score: Optional[list[float]] = None               # parallel to raw_cue_points_ms
    n_invalid_cue_predictions: Optional[int] = None
    invalid_cue_points_raw_ms: Optional[list[float]] = None   # the raw values filtered out (outside [0, duration_ms])
    # cue_score is a per-cue numeric score whose MEANING is declared by
    # cue_score_kind (e.g. "MINMAX_NORMALIZED_DETR_DETECTION_SCORE") -- never
    # implied to be a calibrated confidence unless it genuinely is one.
    # cue_confidence stays null/UNKNOWN unless a candidate emits an actually
    # calibrated musical-cue confidence (PM REPAIR R5/R9).
    cue_score: Optional[list[float]] = None                # parallel to cue_points_ms (validated set only)
    cue_score_kind: Optional[str] = None
    cue_confidence: Optional[list[float]] = None            # parallel to cue_points_ms; None unless calibrated

    phrase_boundaries_ms: Optional[list[float]] = None
    section_boundaries: Optional[list[dict]] = None        # [{"t_start_ms","t_end_ms","label"}]

    # --- runtime / portability fields (Issue #5 Task E; repaired per PM
    # REPAIR R1, then again per PM REVIEW #2 R8/R9) ---
    #
    # R8: canonical AnalyzerResult rows (the ones feeding all_raw.json /
    # metrics.json / lane decisions) are produced by a FRESH model/estimator
    # construction on every single call -- never a cross-fixture cached
    # object -- specifically so correctness fields above (beat_timestamps_ms,
    # cue_points_ms, etc.) can never be contaminated by another fixture's
    # prior state. `estimator_lifecycle` records this methodology directly
    # on every canonical row:
    #   "N_A"             -- baselines: no model to load, concept doesn't apply
    #   "FRESH_PER_CALL"   -- ML candidates: a brand-new model/estimator was
    #                         constructed for THIS call and used for nothing else
    # A SEPARATE, non-canonical warm-reuse profiling pass (results/runtime_profile.json,
    # produced by eval/run_runtime_profile.py) deliberately reuses one
    # model/estimator across multiple fixtures purely to measure the
    # cold-vs-warm wall-clock difference; its records use
    # "COLD_MODEL_LOAD_INFERENCE" / "WARM_INFERENCE" and are never merged
    # into all_raw.json/metrics.json. A dedicated same-fixture equivalence
    # test (results/warm_cold_equivalence.json) independently checks whether
    # that warm-reuse profiling path would even be safe to use for
    # correctness, without ever feeding its own output back into canonical
    # results either.
    #
    # R9: four non-overlapping timing fields replace the single ambiguous
    # wall_time_sec/asset_fetch_wall_sec pair from the R1 repair:
    #   model_load_wall_sec -- local construction/deserialization/
    #                           model-to-device time only (starts when
    #                           construction begins, ends when the model/
    #                           estimator object is ready to run inference)
    #   asset_fetch_wall_sec -- network/download time only, IF actually
    #                           separately measured; both candidates in this
    #                           harness load already-cached local checkpoints
    #                           at run time (no runtime network fetch is
    #                           separately instrumented), so this is null on
    #                           every row produced by this harness -- never
    #                           conflated with model_load_wall_sec
    #   inference_wall_sec   -- audio preprocessing + actual model forward
    #                           pass + post-processing; timer starts strictly
    #                           AFTER model_load_wall_sec's timer has stopped
    #   total_call_wall_sec  -- the full observed call, defined to equal
    #                           model_load_wall_sec + inference_wall_sec
    #                           exactly (0.0 treated as the additive identity
    #                           when a field is None because that phase did
    #                           not occur on this call) -- verified by
    #                           eval/verify_repair.py, never itself claimed
    #                           to be inference-only
    estimator_lifecycle: Optional[str] = None
    model_load_wall_sec: Optional[float] = None
    asset_fetch_wall_sec: Optional[float] = None
    inference_wall_sec: Optional[float] = None
    total_call_wall_sec: Optional[float] = None
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
