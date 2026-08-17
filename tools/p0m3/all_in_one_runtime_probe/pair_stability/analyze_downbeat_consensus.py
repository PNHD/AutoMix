"""P0-M3-R3 RM041<->RM014 evidence stability -- A2/A3 cross-seed metrics.

Loads the 10 raw per-(track,seed) run files produced by
``run_cross_seed_stability.py`` and computes:

A2: per-track BPM (each seed/mode/min/max) and beat/downbeat grid
cross-seed stability -- both a full bidirectional ALL-PAIRS statistic
(every one of the 10 seed-pairs, both directions pooled) and a
baseline-vs-other-seed statistic (seed 0 vs each of seeds 1-4).

A3: boundary-local downbeat/beat evidence at the exact accepted boundary
(RM041 exit 186456.2 ms, RM014 entry 0.0 ms) for every seed, compared in
BOTH directions against the accepted madmom benchmark grid from
``tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json``.

No cherry-picking: all 5 seeds per track are used unconditionally.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

TRACKS = ["RM041", "RM014"]
SEEDS = [0, 1, 2, 3, 4]
COVERAGE_THRESHOLDS_MS = [25, 50, 100]

BOUNDARY_TARGET_MS = {"RM041": 186456.2, "RM014": 0.0}
BOUNDARY_ROLE = {"RM041": "outgoing_exit", "RM014": "incoming_entry"}


def load_runs(raw_dir: Path) -> dict:
    runs = {}
    for track in TRACKS:
        runs[track] = {}
        for seed in SEEDS:
            path = raw_dir / f"{track}-seed{seed}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload["run"]["execution_result"] != "PASS":
                raise ValueError(f"NON_PASS_RUN_{track}_SEED{seed}")
            runs[track][seed] = payload["run"]
    return runs


def bidirectional_nearest_distances(a: list[float], b: list[float]) -> list[float]:
    if not a or not b:
        return []
    dists = []
    for va in a:
        dists.append(min(abs(va - vb) for vb in b))
    for vb in b:
        dists.append(min(abs(vb - va) for va in a))
    return dists


def dist_stats(dists: list[float]) -> dict:
    if not dists:
        return {"median_ms": None, "p90_ms": None, "max_ms": None,
                "coverage": {f"le_{t}ms": None for t in COVERAGE_THRESHOLDS_MS}, "n": 0}
    sorted_d = sorted(dists)
    n = len(sorted_d)

    def pct(p):
        if n == 1:
            return sorted_d[0]
        idx = min(n - 1, max(0, round(p * (n - 1))))
        return sorted_d[idx]

    return {
        "median_ms": round(statistics.median(sorted_d), 3),
        "p90_ms": round(pct(0.90), 3),
        "max_ms": round(sorted_d[-1], 3),
        "coverage": {
            f"le_{t}ms": round(sum(1 for d in sorted_d if d <= t) / n, 4)
            for t in COVERAGE_THRESHOLDS_MS
        },
        "n": n,
    }


def grid_cross_seed_stats(per_seed_grid: dict[int, list[float]]) -> dict:
    all_pairs_dists: list[float] = []
    pairwise_breakdown = []
    seeds = sorted(per_seed_grid.keys())
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            s1, s2 = seeds[i], seeds[j]
            d = bidirectional_nearest_distances(per_seed_grid[s1], per_seed_grid[s2])
            all_pairs_dists.extend(d)
            pairwise_breakdown.append({
                "seed_a": s1, "seed_b": s2,
                "stats": dist_stats(d),
            })

    baseline = per_seed_grid[0]
    baseline_vs_other = []
    baseline_dists: list[float] = []
    for seed in seeds:
        if seed == 0:
            continue
        d = bidirectional_nearest_distances(baseline, per_seed_grid[seed])
        baseline_dists.extend(d)
        baseline_vs_other.append({"seed": seed, "stats": dist_stats(d)})

    return {
        "counts_per_seed": {seed: len(per_seed_grid[seed]) for seed in seeds},
        "all_pairs_bidirectional": dist_stats(all_pairs_dists),
        "all_pairs_breakdown": pairwise_breakdown,
        "baseline_seed0_vs_other_bidirectional": dist_stats(baseline_dists),
        "baseline_seed0_vs_other_breakdown": baseline_vs_other,
    }


def bpm_stats(per_seed_bpm: dict[int, float]) -> dict:
    values = [per_seed_bpm[s] for s in sorted(per_seed_bpm.keys())]
    counts = Counter(values)
    mode_value, mode_count = counts.most_common(1)[0]
    return {
        "per_seed": {seed: per_seed_bpm[seed] for seed in sorted(per_seed_bpm.keys())},
        "mode": mode_value,
        "mode_agreement_fraction": round(mode_count / len(values), 4),
        "min": min(values),
        "max": max(values),
        "all_identical": len(set(values)) == 1,
    }


def nearest_and_signed(target_ms: float, events: list[float]) -> dict:
    if not events:
        return {"nearest_ms": None, "signed_distance_ms": None, "abs_distance_ms": None}
    nearest = min(events, key=lambda v: abs(v - target_ms))
    signed = nearest - target_ms
    return {"nearest_ms": round(nearest, 3), "signed_distance_ms": round(signed, 3), "abs_distance_ms": round(abs(signed), 3)}


def local_interval(events: list[float], nearest_ms: float | None) -> float | None:
    if nearest_ms is None or len(events) < 2:
        return None
    idx = min(range(len(events)), key=lambda i: abs(events[i] - nearest_ms))
    diffs = []
    if idx > 0:
        diffs.append(events[idx] - events[idx - 1])
    if idx + 1 < len(events):
        diffs.append(events[idx + 1] - events[idx])
    return round(statistics.mean(diffs), 3) if diffs else None


def madmom_benchmark_boundary(prior_downbeats: list[float], target_ms: float) -> dict:
    nb = nearest_and_signed(target_ms, prior_downbeats)
    interval = local_interval(prior_downbeats, nb["nearest_ms"])
    return {**nb, "local_downbeat_interval_ms": interval}


def boundary_local_evidence(track: str, runs_for_track: dict[int, dict], madmom_downbeats: list[float]) -> dict:
    target_ms = BOUNDARY_TARGET_MS[track]
    per_seed = {}
    phases = []
    for seed in SEEDS:
        output = runs_for_track[seed]["semantic_output"]
        beats = output["beats_ms"]
        downbeats = output["downbeats_ms"]
        beat_positions = output["beat_positions"]
        meter = max(beat_positions) if beat_positions else None

        nb_beat = nearest_and_signed(target_ms, beats)
        nb_downbeat = nearest_and_signed(target_ms, downbeats)
        beat_interval = local_interval(beats, nb_beat["nearest_ms"])
        downbeat_interval = local_interval(downbeats, nb_downbeat["nearest_ms"])
        bar_duration_ms = round(downbeat_interval, 3) if downbeat_interval else (
            round(beat_interval * meter, 3) if beat_interval and meter else None
        )
        position_in_bar = None
        if nb_beat["nearest_ms"] is not None and beats:
            idx = min(range(len(beats)), key=lambda i: abs(beats[i] - nb_beat["nearest_ms"]))
            if idx < len(beat_positions):
                position_in_bar = beat_positions[idx]

        madmom_cmp = madmom_benchmark_boundary(madmom_downbeats, target_ms)
        # bidirectional agreement: this seed's nearest downbeat vs madmom's nearest downbeat to the SAME target,
        # plus the reverse direction (nearest madmom downbeat to this seed's own detected downbeat time).
        reverse = None
        if nb_downbeat["nearest_ms"] is not None and madmom_downbeats:
            reverse = nearest_and_signed(nb_downbeat["nearest_ms"], madmom_downbeats)

        per_seed[seed] = {
            "meter_used": meter,
            "nearest_beat": nb_beat,
            "nearest_downbeat": nb_downbeat,
            "position_in_bar_of_nearest_beat": position_in_bar,
            "local_downbeat_interval_ms": downbeat_interval,
            "local_bar_duration_ms": bar_duration_ms,
            "madmom_benchmark_nearest_downbeat_to_target": madmom_cmp,
            "reverse_madmom_nearest_to_this_seed_downbeat": reverse,
            "forward_vs_madmom_abs_diff_ms": (
                round(abs(nb_downbeat["nearest_ms"] - madmom_cmp["nearest_ms"]), 3)
                if nb_downbeat["nearest_ms"] is not None and madmom_cmp["nearest_ms"] is not None else None
            ),
        }
        if position_in_bar is not None:
            phases.append(position_in_bar)

    phase_consistency = {
        "distinct_positions_in_bar_across_seeds": sorted(set(phases)),
        "phase_consistent_across_all_seeds": len(set(phases)) <= 1 if phases else None,
    }

    forward_diffs = [row["forward_vs_madmom_abs_diff_ms"] for row in per_seed.values() if row["forward_vs_madmom_abs_diff_ms"] is not None]
    reverse_diffs = [
        row["reverse_madmom_nearest_to_this_seed_downbeat"]["abs_distance_ms"]
        for row in per_seed.values()
        if row["reverse_madmom_nearest_to_this_seed_downbeat"] is not None
        and row["reverse_madmom_nearest_to_this_seed_downbeat"]["abs_distance_ms"] is not None
    ]
    combined = forward_diffs + reverse_diffs

    return {
        "target_ms": target_ms,
        "role": BOUNDARY_ROLE[track],
        "per_seed": per_seed,
        "phase_consistency": phase_consistency,
        "vs_madmom_benchmark_bidirectional_stats": dist_stats(combined),
        "vs_madmom_benchmark_forward_only_stats": dist_stats(forward_diffs),
        "vs_madmom_benchmark_reverse_only_stats": dist_stats(reverse_diffs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--accepted-analyzer-evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    runs = load_runs(raw_dir)
    accepted = json.loads(Path(args.accepted_analyzer_evidence).read_text(encoding="utf-8"))

    output = {"schema_version": 1, "scope": "RM041, RM014 ONLY", "seeds_used": SEEDS, "tracks": {}}

    for track in TRACKS:
        per_seed_bpm = {s: runs[track][s]["semantic_output"]["bpm"] for s in SEEDS}
        per_seed_beats = {s: runs[track][s]["semantic_output"]["beats_ms"] for s in SEEDS}
        per_seed_downbeats = {s: runs[track][s]["semantic_output"]["downbeats_ms"] for s in SEEDS}

        madmom_downbeats = [float(v) for v in accepted["tracks"][track]["downbeat"]["downbeats_ms"]]

        output["tracks"][track] = {
            "bpm": bpm_stats(per_seed_bpm),
            "beat_grid_cross_seed": grid_cross_seed_stats(per_seed_beats),
            "downbeat_grid_cross_seed": grid_cross_seed_stats(per_seed_downbeats),
            "boundary_local_downbeat_evidence": boundary_local_evidence(track, runs[track], madmom_downbeats),
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    for track in TRACKS:
        t = output["tracks"][track]
        print(f"{track}: bpm_mode={t['bpm']['mode']} bpm_all_identical={t['bpm']['all_identical']} "
              f"beat_median_ms={t['beat_grid_cross_seed']['all_pairs_bidirectional']['median_ms']} "
              f"downbeat_median_ms={t['downbeat_grid_cross_seed']['all_pairs_bidirectional']['median_ms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
