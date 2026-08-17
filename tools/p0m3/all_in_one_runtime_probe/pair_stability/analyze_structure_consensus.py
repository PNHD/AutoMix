"""P0-M3-R3 RM041<->RM014 evidence stability -- A4 functional structure stability.

For the exact accepted boundary (RM041 exit 186456.2 ms, RM014 entry
0.0 ms), records the ACTUAL All-In-One functional-segment label
containing the boundary for every seed, and computes label consensus and
boundary-displacement statistics across seeds. Uses only labels literally
returned by the model (``AnalysisResult.segments``) -- never a fabricated
phrase/outro/intro claim.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

TRACKS = ["RM041", "RM014"]
SEEDS = [0, 1, 2, 3, 4]
BOUNDARY_TARGET_MS = {"RM041": 186456.2, "RM014": 0.0}
BOUNDARY_ROLE = {"RM041": "outgoing_exit", "RM014": "incoming_entry"}


def load_runs(raw_dir: Path) -> dict:
    runs = {}
    for track in TRACKS:
        runs[track] = {}
        for seed in SEEDS:
            payload = json.loads((raw_dir / f"{track}-seed{seed}.json").read_text(encoding="utf-8"))
            if payload["run"]["execution_result"] != "PASS":
                raise ValueError(f"NON_PASS_RUN_{track}_SEED{seed}")
            runs[track][seed] = payload["run"]
    return runs


def segment_containing(segments: list[dict], target_ms: float) -> tuple[int, dict]:
    for i, seg in enumerate(segments):
        if seg["start_ms"] <= target_ms < seg["end_ms"] or (i == len(segments) - 1 and target_ms == seg["end_ms"]):
            return i, seg
    # target beyond the last segment's end (shouldn't happen given track duration, but handled honestly)
    return len(segments) - 1, segments[-1]


def nearest_functional_boundary(segments: list[dict], target_ms: float) -> dict:
    boundaries = sorted({v for seg in segments for v in (seg["start_ms"], seg["end_ms"])})
    nearest = min(boundaries, key=lambda v: abs(v - target_ms))
    return {"nearest_ms": nearest, "signed_distance_ms": round(nearest - target_ms, 3), "abs_distance_ms": round(abs(nearest - target_ms), 3)}


def beats_bars_distance(distance_ms: float, beats: list[float], meter: int | None) -> dict:
    beat_interval = statistics.median(b - a for a, b in zip(beats, beats[1:])) if len(beats) > 1 else None
    beats_dist = round(distance_ms / beat_interval, 3) if beat_interval else None
    bars_dist = round(distance_ms / (beat_interval * meter), 3) if beat_interval and meter else None
    return {"distance_beats": beats_dist, "distance_bars": bars_dist}


def track_structure_consensus(track: str, runs_for_track: dict[int, dict]) -> dict:
    target_ms = BOUNDARY_TARGET_MS[track]
    per_seed = {}
    labels = []
    boundary_distances = []
    for seed in SEEDS:
        output = runs_for_track[seed]["semantic_output"]
        segments = output["segments"]
        beats = output["beats_ms"]
        beat_positions = output["beat_positions"]
        meter = max(beat_positions) if beat_positions else None

        idx, segment = segment_containing(segments, target_ms)
        prev_label = segments[idx - 1]["label"] if idx > 0 else None
        next_label = segments[idx + 1]["label"] if idx + 1 < len(segments) else None
        nearest = nearest_functional_boundary(segments, target_ms)
        bb = beats_bars_distance(nearest["abs_distance_ms"], beats, meter)

        per_seed[seed] = {
            "segment_index": idx,
            "functional_label": segment["label"],
            "segment_start_ms": segment["start_ms"],
            "segment_end_ms": segment["end_ms"],
            "previous_label": prev_label,
            "next_label": next_label,
            "nearest_functional_section_boundary": nearest,
            "distance_beats": bb["distance_beats"],
            "distance_bars": bb["distance_bars"],
            "meter_used": meter,
            "functional_label_from_actual_output": True,
            "phrase_claimed": False,
        }
        labels.append(segment["label"])
        boundary_distances.append(nearest["abs_distance_ms"])

    label_counts = Counter(labels)
    top_label, top_count = label_counts.most_common(1)[0]
    sorted_bd = sorted(boundary_distances)
    n = len(sorted_bd)

    def pct(p):
        if n == 1:
            return sorted_bd[0]
        idx = min(n - 1, max(0, round(p * (n - 1))))
        return sorted_bd[idx]

    return {
        "role": BOUNDARY_ROLE[track],
        "target_ms": target_ms,
        "per_seed": per_seed,
        "label_counts": dict(label_counts),
        "label_consensus_fraction": round(top_count / len(labels), 4),
        "modal_label": top_label,
        "boundary_displacement_ms": {
            "median": round(statistics.median(sorted_bd), 3),
            "p90": round(pct(0.90), 3),
            "max": round(sorted_bd[-1], 3),
        },
        "same_functional_role_across_all_seeds": len(label_counts) == 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    runs = load_runs(raw_dir)

    output = {
        "schema_version": 1,
        "scope": "RM041, RM014 ONLY",
        "seeds_used": SEEDS,
        "tracks": {track: track_structure_consensus(track, runs[track]) for track in TRACKS},
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    for track in TRACKS:
        t = output["tracks"][track]
        print(f"{track}: modal_label={t['modal_label']} consensus_fraction={t['label_consensus_fraction']} "
              f"same_role_all_seeds={t['same_functional_role_across_all_seeds']} "
              f"boundary_displacement_median_ms={t['boundary_displacement_ms']['median']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
