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

    cue_points_ms: Optional[list[float]] = None
    cue_confidence: Optional[list[float]] = None          # parallel to cue_points_ms

    phrase_boundaries_ms: Optional[list[float]] = None
    section_boundaries: Optional[list[dict]] = None        # [{"t_start_ms","t_end_ms","label"}]

    # --- runtime / portability fields (Issue #5 Task E) ---
    wall_time_sec: Optional[float] = None
    is_cold_run: Optional[bool] = None
    peak_memory_mb: Optional[float] = None
    device: Optional[str] = None            # "cpu" | "cuda:0" | "N/A"
    model_checkpoint_size_mb: Optional[float] = None

    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
