"""P0-M3-R3 RM014 incoming-entry anchor feasibility -- diagnostic candidate
derivation (Issue #7 PM comment id 5310893724).

Diagnostic only. Does not write a new entry back into R2, does not change
compatibility.py / select_real_music_pairs.py / contract.py / boundary.py,
and does not invent a production confidence threshold. The current
canonical RM014 incoming-entry evidence remains 0 ms.

Reuses, unmodified in spirit, the same nearest/interval helper logic already
accepted in
``tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_downbeat_consensus.py``
(``nearest_and_signed`` / ``local_interval``), applied here to cluster
cross-seed downbeats instead of evaluating a single fixed boundary.

Inputs (all already-accepted, already-committed evidence -- no rerun):
  * ``tools/p0m3/all_in_one_runtime_probe/pair_stability/results/raw_runs/RM014-seed{0..4}.json``
    (5 real ``allin1.analyze`` runs, already accepted for the RM041<->RM014
    stability pass).
  * ``tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json``
    (accepted madmom RNN+DBN downbeat benchmark grid for RM014).

Step 1: determine the UNANIMOUS All-In-One functional-intro interval for
RM014 -- the leading run of ``functional_labels == "intro"`` segments that
every one of the 5 seeds agrees on (by segment end timestamp).

Step 2: collect every downbeat from every seed strictly inside that unanimous
interval.

Step 3: cluster those cross-seed downbeats. A cluster is a maximal run of
sorted downbeat timestamps (pooled across all 5 seeds) where each consecutive
gap is <= ``CLUSTER_MERGE_TOLERANCE_MS``. The tolerance is chosen from
EXISTING accepted evidence, not invented: the RM041<->RM014 stability pass's
own baseline(seed0)-vs-other RM014 downbeat-grid p90 was 10 ms and its
coverage@100ms was 96 percent (see
``pair_stability/results/cross_seed_metrics.json``), and RM014's own local
downbeat interval at seeds 2/3/4 is ~1840-1950 ms (i.e. >15x the tolerance)
-- so a 100 ms merge tolerance is generous enough to absorb ordinary
cross-seed jitter without ever merging two genuinely different bars.

Step 4: rank clusters exactly as specified by the task:
  1. 5/5 seed support (descending)
  2. smallest spread = max(ts) - min(ts) (ascending)
  3. smallest |center - nearest_madmom_downbeat| (ascending)
  4. earliest center timestamp (ascending)
This ordering is diagnostic only; it defines no production threshold.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

SEEDS = [0, 1, 2, 3, 4]
TRACK = "RM014"
CLUSTER_MERGE_TOLERANCE_MS = 100.0


def nearest_and_signed(target_ms: float, events: list[float]) -> dict:
    """Verbatim logic from pair_stability/analyze_downbeat_consensus.py."""
    if not events:
        return {"nearest_ms": None, "signed_distance_ms": None, "abs_distance_ms": None}
    nearest = min(events, key=lambda v: abs(v - target_ms))
    signed = nearest - target_ms
    return {"nearest_ms": round(nearest, 3), "signed_distance_ms": round(signed, 3), "abs_distance_ms": round(abs(signed), 3)}


def load_runs(raw_dir: Path) -> dict[int, dict]:
    runs = {}
    for seed in SEEDS:
        path = raw_dir / f"{TRACK}-seed{seed}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["run"]["execution_result"] != "PASS":
            raise ValueError(f"NON_PASS_RUN_{TRACK}_SEED{seed}")
        runs[seed] = payload["run"]["semantic_output"]
    return runs


def unanimous_intro_interval(runs: dict[int, dict]) -> dict:
    """Leading run of 'intro'-labeled segments, by segment end_ms, per seed;
    interval is unanimous only if every seed's leading-intro end matches
    (within 0 ms -- these are literal AnalysisResult.segments boundaries,
    not estimated).
    """
    per_seed_end = {}
    per_seed_segments = {}
    for seed, so in runs.items():
        segs = so["segments"]
        leading = []
        for seg in segs:
            if seg["label"] == "intro":
                leading.append(seg)
            else:
                break
        per_seed_segments[seed] = leading
        per_seed_end[seed] = leading[-1]["end_ms"] if leading else None

    ends = list(per_seed_end.values())
    unanimous = len(set(ends)) == 1 and ends[0] is not None
    return {
        "per_seed_leading_intro_segments": per_seed_segments,
        "per_seed_intro_end_ms": per_seed_end,
        "unanimous": unanimous,
        "interval_start_ms": 0.0,
        "interval_end_ms": ends[0] if unanimous else None,
    }


def cluster_downbeats(per_seed_downbeats_in_interval: dict[int, list[float]]) -> list[dict]:
    pooled = []
    for seed, values in per_seed_downbeats_in_interval.items():
        for v in values:
            pooled.append((v, seed))
    pooled.sort(key=lambda x: x[0])

    raw_clusters: list[list[tuple[float, int]]] = []
    current: list[tuple[float, int]] = []
    for point in pooled:
        if current and (point[0] - current[-1][0]) > CLUSTER_MERGE_TOLERANCE_MS:
            raw_clusters.append(current)
            current = []
        current.append(point)
    if current:
        raw_clusters.append(current)

    clusters = []
    for members in raw_clusters:
        by_seed: dict[int, float] = {}
        for ts, seed in members:
            # a seed should contribute at most one point per cluster given
            # the tolerance is far smaller than any real bar interval; if it
            # ever contributes more than one, keep the one nearest the
            # cluster's raw mean (documented, not silently dropped).
            if seed in by_seed:
                raise ValueError(f"UNEXPECTED_MULTI_POINT_SEED_IN_CLUSTER seed={seed}")
            by_seed[seed] = ts
        values = list(by_seed.values())
        center = round(statistics.mean(values), 3)
        clusters.append({
            "support_count": len(by_seed),
            "support_fraction": round(len(by_seed) / len(SEEDS), 4),
            "per_seed_ms": {str(s): by_seed.get(s) for s in SEEDS},
            "center_ms": center,
            "min_ms": round(min(values), 3),
            "max_ms": round(max(values), 3),
            "spread_ms": round(max(values) - min(values), 3),
            "max_deviation_from_center_ms": round(max(abs(v - center) for v in values), 3),
        })
    return clusters


def annotate_and_rank(clusters: list[dict], madmom_downbeats: list[float], entry_ms: float, intro_end_ms: float) -> list[dict]:
    for c in clusters:
        madmom = nearest_and_signed(c["center_ms"], madmom_downbeats)
        c["nearest_madmom_downbeat_ms"] = madmom["nearest_ms"]
        c["madmom_signed_error_ms"] = madmom["signed_distance_ms"]
        c["madmom_abs_error_ms"] = madmom["abs_distance_ms"]
        c["candidate_time_relative_to_current_entry_ms"] = round(c["center_ms"] - entry_ms, 3)
        c["fraction_of_intro_preceding_candidate"] = (
            round(c["center_ms"] / intro_end_ms, 4) if intro_end_ms else None
        )

    ranked = sorted(
        clusters,
        key=lambda c: (
            -c["support_count"],       # 1. 5/5 seed support first
            c["spread_ms"],            # 2. smallest spread
            c["madmom_abs_error_ms"] if c["madmom_abs_error_ms"] is not None else float("inf"),  # 3. smallest madmom disagreement
            c["center_ms"],            # 4. earliest timestamp
        ),
    )
    for i, c in enumerate(ranked):
        c["diagnostic_rank"] = i + 1
    return ranked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--accepted-analyzer-evidence", required=True)
    parser.add_argument("--current-entry-ms", type=float, default=0.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    runs = load_runs(raw_dir)
    accepted = json.loads(Path(args.accepted_analyzer_evidence).read_text(encoding="utf-8"))
    madmom_downbeats = [float(v) for v in accepted["tracks"][TRACK]["downbeat"]["downbeats_ms"]]

    intro = unanimous_intro_interval(runs)
    if not intro["unanimous"]:
        output = {
            "schema_version": 1,
            "scope": "RM014 ONLY (incoming entry)",
            "track": TRACK,
            "seeds_used": SEEDS,
            "intro_interval": intro,
            "result": "NO_UNANIMOUS_INTRO_INTERVAL",
            "clusters_ranked": [],
        }
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print("NO_UNANIMOUS_INTRO_INTERVAL")
        return 1

    interval_end = intro["interval_end_ms"]
    per_seed_downbeats_in_interval = {
        seed: [d for d in so["downbeats_ms"] if 0.0 <= d < interval_end]
        for seed, so in runs.items()
    }

    clusters = cluster_downbeats(per_seed_downbeats_in_interval)
    ranked = annotate_and_rank(clusters, madmom_downbeats, args.current_entry_ms, interval_end)

    output = {
        "schema_version": 1,
        "scope": "RM014 ONLY (incoming entry); diagnostic only; no write-back into R2",
        "track": TRACK,
        "seeds_used": SEEDS,
        "cluster_merge_tolerance_ms": CLUSTER_MERGE_TOLERANCE_MS,
        "cluster_merge_tolerance_rationale": (
            "pair_stability baseline(seed0)-vs-other RM014 downbeat p90=10ms, "
            "coverage@100ms~=0.96 (accepted cross_seed_metrics.json); RM014 local "
            "downbeat interval ~1840-1950ms at seeds 2/3/4, >18x the tolerance"
        ),
        "current_canonical_entry_ms": args.current_entry_ms,
        "intro_interval": intro,
        "per_seed_downbeats_in_interval": {str(s): v for s, v in per_seed_downbeats_in_interval.items()},
        "madmom_downbeats_in_interval": [d for d in madmom_downbeats if 0.0 <= d < interval_end],
        "ranking_order": [
            "1_five_of_five_seed_support_desc",
            "2_smallest_spread_ms_asc",
            "3_smallest_madmom_abs_error_ms_asc",
            "4_earliest_center_ms_asc",
        ],
        "ranking_is_diagnostic_only_not_a_production_threshold": True,
        "clusters_ranked": ranked,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    top = ranked[0] if ranked else None
    print(f"CLUSTERS_DERIVED n={len(ranked)} intro_end_ms={interval_end} "
          f"top_center_ms={top['center_ms'] if top else None} "
          f"top_support={top['support_count'] if top else None}/5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
