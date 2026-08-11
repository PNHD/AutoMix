"""
Negative baseline #1 (Issue #5 "REQUIRED NEGATIVE BASELINES"): scalar-BPM
theoretical grid, beat_ts[i] = i * (60000 / BPM), starting at t=0.

This is deliberately the SAME mechanism the P0-M2 benchmark contract's
terminology gate calls out as NOT beat-aware (Sec 3.1: "a derived
60000/BPM theoretical grid (SimpMusic's actual mechanism, P0-M1 Sec 8
level 2)"). It is included here to be measured, not recommended: it has
zero phase information (assumes the grid starts exactly at t=0) and zero
downbeat/meter/cue/phrase/section information by construction.

Independent implementation; no GPL/AGPL source consulted or copied
(scope prohibition, Issue #5 "REQUIRED NEGATIVE BASELINES").
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "..")
from common.schema import AnalyzerResult  # noqa: E402


def run(fixture_id: str, gt: dict) -> AnalyzerResult:
    t0 = time.perf_counter()
    bpm = gt.get("bpm")
    duration_sec = gt["duration_sec"]
    result = AnalyzerResult(
        candidate_id="scalar_bpm_grid_baseline",
        candidate_kind="BASELINE",
        fixture_id=fixture_id,
        run_state="OK",
        notes="Negative baseline: theoretical i*(60000/BPM) grid from t=0. "
              "No phase/downbeat/meter/cue/phrase/section awareness by construction.",
    )
    if bpm is None:
        result.run_state = "FAILED"
        result.error = "no scalar BPM metadata available for this fixture"
        return result

    beat_period_ms = 60000.0 / bpm
    n_beats = int(duration_sec * 1000 / beat_period_ms) + 1
    beats = [round(i * beat_period_ms, 3) for i in range(n_beats)]

    result.bpm = bpm
    result.bpm_confidence = 1.0  # metadata is exact for synthetic fixtures; the FAILURE MODE is phase, not BPM value
    result.beat_timestamps_ms = beats
    result.beat_confidence = None  # theoretical grid asserts no measured confidence
    result.downbeat_timestamps_ms = None  # scalar BPM alone cannot determine bar phase
    result.device = "cpu"
    result.wall_time_sec = time.perf_counter() - t0
    result.run_phase = "N_A"  # PM REPAIR R1: no model to load; lifecycle concept doesn't apply
    result.memory_measurement_method = "N_A"
    return result
