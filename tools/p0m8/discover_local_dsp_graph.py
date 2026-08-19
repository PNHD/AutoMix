"""
P0-M8-R1 -- LocalDSP consumer quality slice: successor-graph discovery.

Builds the FULL eligible-pair graph across the 100-track owner-supplied
local corpus by reusing `pair_discovery.py`'s `evaluate_pair` function
UNMODIFIED (imported, not copied/reimplemented) -- the same cached-evidence-
only eligibility test (Beat This beat/downbeat cache + Stage-B corpus
analysis + <=6% direct tempo-ratio rule + octave guard + structure
confidence) that produced the already-accepted P0-M5-R1 frozen 8-pair
manifest. This script does NOT run Beat This, does NOT add a new beat
model, and does NOT compute any new per-track audio analysis -- it only
enumerates ordered pairs over the SAME already-cached evidence
`pair_discovery.py` already reads, so a genuine multi-hop successor CHAIN
(needed for automatic continuation across >=3 handoffs) can be discovered,
instead of being restricted to the disconnected 8-pair "single demo edge
each" set that P0-M5-R1 froze for its own (different) appearance-capped
purpose.

Output: tools/p0m8/local_dsp_graph.json -- the full eligible-pair adjacency
list (out_id -> [{in_id, ...eligibility evidence...}]) plus one greedily
selected consumer-flow chain (a walk with no repeated track) of at least 4
tracks (>=3 transitions), preferring near-native tempo (tempo_correction
~0, so the live two-deck runtime crossfade path can be used with no new
Signalsmith stretch rendering needed) and HIGH structure confidence, ranked
identically to pair_discovery.py's own soft_rank_key.

Usage:
    python tools/p0m8/discover_local_dsp_graph.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
P0M5_DIR = REPO_ROOT / "tools" / "p0m5" / "apple_like_vertical_slice"
sys.path.insert(0, str(P0M5_DIR))

import pair_discovery as pd  # noqa: E402 (reused unmodified)

OUT_PATH = HERE / "local_dsp_graph.json"
CHAIN_MIN_TRACKS = 4  # >= 3 transitions
NEAR_NATIVE_MAX_CORRECTION = 0.005  # stay in the live two-deck (no-stretch) band


def main() -> int:
    analysis = pd.load_json(pd.CORPUS_DIR / "corpus_analysis.local.json")
    beat_cache_dir = P0M5_DIR / "work_local" / "beat_cache"
    beat_aggregate = pd.load_json(P0M5_DIR / "beat_analysis_aggregate_sanitized.json")
    ids = sorted(analysis.keys())

    eligible = []
    reason_counts: dict[str, int] = {}
    for out_id in ids:
        for in_id in ids:
            if out_id == in_id:
                continue
            ev = pd.evaluate_pair(out_id, in_id, analysis, beat_cache_dir, beat_aggregate)
            if ev["eligible"]:
                eligible.append((out_id, in_id, ev))
            else:
                reason_counts[ev["reason"]] = reason_counts.get(ev["reason"], 0) + 1

    print(f"Eligible ordered pairs: {len(eligible)} / {len(ids) * (len(ids) - 1)}")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1])[:8]:
        print(f"  ineligible[{reason}] = {count}")

    adjacency: dict[str, list] = {}
    by_pair = {}
    for out_id, in_id, ev in eligible:
        adjacency.setdefault(out_id, []).append({"in_id": in_id, **ev})
        by_pair[(out_id, in_id)] = ev
    for out_id in adjacency:
        adjacency[out_id].sort(key=lambda e: pd.soft_rank_key(pd.build_pair_id(out_id, e["in_id"]), e))

    # Load the already-frozen/accepted dev pairs so the chain search prefers
    # reusing already-rendered audio (S01/S04-S08) before pulling in a brand
    # new pair that would need fresh ffmpeg trimming.
    frozen = pd.load_json(P0M5_DIR / "pair_manifest_sanitized.json")
    frozen_dev_edges = {(p["out_id"], p["in_id"]) for p in frozen["pairs"] if p["split"] == "dev"}

    def edge_rank(out_id: str, e: dict) -> tuple:
        already_rendered = 0 if (out_id, e["in_id"]) in frozen_dev_edges else 1
        near_native = 0 if e["tempo_correction"] <= NEAR_NATIVE_MAX_CORRECTION else 1
        return (already_rendered, near_native) + pd.soft_rank_key(pd.build_pair_id(out_id, e["in_id"]), e)

    best_chain: list[str] = []
    best_edges: list[dict] = []

    def dfs(path: list[str], edges: list[dict], depth_limit: int):
        nonlocal best_chain, best_edges
        if len(path) > len(best_chain):
            best_chain, best_edges = list(path), list(edges)
        if len(path) >= depth_limit:
            return
        cur = path[-1]
        candidates = sorted(adjacency.get(cur, []), key=lambda e: edge_rank(cur, e))
        for e in candidates:
            if e["in_id"] in path:
                continue
            path.append(e["in_id"])
            edges.append({"out_id": cur, **e})
            dfs(path, edges, depth_limit)
            path.pop()
            edges.pop()
            if len(best_chain) >= depth_limit:
                return

    # Search from every track that already has a frozen dev out-edge first
    # (reuse bias), then fall back to any track, stopping once a chain of
    # CHAIN_MIN_TRACKS is found.
    seed_priority = sorted(
        adjacency.keys(),
        key=lambda t: (0 if any(o == t for o, _ in frozen_dev_edges) else 1, t),
    )
    depth_limit = max(CHAIN_MIN_TRACKS, 6)
    for seed in seed_priority:
        dfs([seed], [], depth_limit)
        if len(best_chain) >= CHAIN_MIN_TRACKS:
            break

    result = {
        "schema": "p0m8_local_dsp_graph_v1",
        "eligible_pair_count": len(eligible),
        "ineligible_reason_counts": reason_counts,
        "adjacency": adjacency,
        "chain": {
            "tracks": best_chain,
            "transition_count": len(best_edges),
            "edges": best_edges,
        },
    }
    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nBest chain found: {' -> '.join(best_chain)} ({len(best_edges)} transitions)")
    for e in best_edges:
        print(f"  {e['out_id']}->{e['in_id']} tempo_correction={e['tempo_correction']} structure={e['exit_structure_confidence']} already_rendered={(e['out_id'], e['in_id']) in frozen_dev_edges}")
    print(f"\nWrote {OUT_PATH}")
    return 0 if len(best_chain) >= CHAIN_MIN_TRACKS else 1


if __name__ == "__main__":
    raise SystemExit(main())
