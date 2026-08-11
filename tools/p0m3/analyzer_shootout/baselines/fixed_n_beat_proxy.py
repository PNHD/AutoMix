"""
Negative baseline #2 (Issue #5 "REQUIRED NEGATIVE BASELINES"): fixed
every-N-beats phrase proxy, default N=32, per P0-M0 Sec 7.2 / P0-M2
contract Sec 3.1 ("a fixed 'every 32 beats' proxy" is explicitly listed
as NOT satisfying phrase-awareness).

Takes a beat grid (from ground truth OR from another baseline/candidate)
and emits a "phrase boundary" every N beats, with zero regard for actual
musical phrase structure. Included to be measured, not recommended.

Independent implementation; no GPL/AGPL source consulted or copied.
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "..")
from common.schema import AnalyzerResult  # noqa: E402


def run(fixture_id: str, gt: dict, n_beats_per_phrase: int = 32,
        beat_timestamps_ms: list[float] | None = None) -> AnalyzerResult:
    t0 = time.perf_counter()
    beats = beat_timestamps_ms if beat_timestamps_ms is not None else gt.get("beat_timestamps_ms")
    result = AnalyzerResult(
        candidate_id=f"fixed_{n_beats_per_phrase}_beat_phrase_proxy_baseline",
        candidate_kind="BASELINE",
        fixture_id=fixture_id,
        run_state="OK",
        notes=f"Negative baseline: phrase boundary asserted every {n_beats_per_phrase} beats "
              f"from beat 0, with no regard for actual musical structure.",
    )
    if not beats:
        result.run_state = "FAILED"
        result.error = "no input beat grid available (ground truth or upstream baseline)"
        return result

    phrase_boundaries = [beats[i] for i in range(0, len(beats), n_beats_per_phrase)]
    result.phrase_boundaries_ms = phrase_boundaries
    result.device = "cpu"
    result.wall_time_sec = time.perf_counter() - t0
    result.is_cold_run = True
    return result
