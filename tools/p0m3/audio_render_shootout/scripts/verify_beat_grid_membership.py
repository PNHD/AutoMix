"""
PM STAGE A REVIEW R2 repair: "Add a verifier that every FULL_DJ outgoing/
incoming beat target exists in synthetic beats_ms, and every downbeat
target exists in downbeats_ms, within an explicit sample-accurate/
tolerance rule. Apply this assertion to A/B/C, not only B."

This is a PROJECT_INFERENCE diagnostic tolerance (not derived from any
Apple disclosure) -- see docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md
"Apple-like behavioral target -- public evidence vs project inference" for
the evidence-labeling discipline this project follows.

Usage:
    python scripts/verify_beat_grid_membership.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.render_common import load_scenario_context  # noqa: E402

SCENARIOS = ["R3-A", "R3-B", "R3-C"]  # R3-D never offers FULL_DJ_BLEND -- nothing to check
GRID_TOLERANCE_MS = 5.0  # PROJECT_INFERENCE diagnostic tolerance, not Apple-derived

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def nearest_distance_ms(target_ms: float, grid_ms: list) -> float:
    if not grid_ms:
        return float("inf")
    return min(abs(target_ms - g) for g in grid_ms)


def main():
    for tid in SCENARIOS:
        ctx = load_scenario_context(tid)
        decision = ctx["decision"]
        if "FULL_DJ_BLEND" not in decision.get("allowed_transition_class_set", []):
            print(f"SKIP {tid}: FULL_DJ_BLEND not allowed, no alignment targets to check")
            continue

        out_gt = ctx["outgoing_ground_truth"]
        in_gt = ctx["incoming_ground_truth"]

        out_beat_target = decision.get("outgoing_beat_alignment_target_ms")
        out_downbeat_target = decision.get("outgoing_downbeat_alignment_target_ms")
        in_beat_target = decision.get("incoming_beat_alignment_target_ms")
        in_downbeat_target = decision.get("incoming_downbeat_alignment_target_ms")

        if out_beat_target is not None:
            d = nearest_distance_ms(out_beat_target, out_gt["beats_ms"])
            check(d <= GRID_TOLERANCE_MS, f"{tid}: outgoing_beat_alignment_target_ms={out_beat_target} is on beats_ms grid (nearest={d:.4f}ms, tolerance={GRID_TOLERANCE_MS}ms)")

        if out_downbeat_target is not None:
            d = nearest_distance_ms(out_downbeat_target, out_gt["downbeats_ms"])
            check(d <= GRID_TOLERANCE_MS, f"{tid}: outgoing_downbeat_alignment_target_ms={out_downbeat_target} is on downbeats_ms grid (nearest={d:.4f}ms, tolerance={GRID_TOLERANCE_MS}ms)")

        if in_beat_target is not None:
            d = nearest_distance_ms(in_beat_target, in_gt["beats_ms"])
            check(d <= GRID_TOLERANCE_MS, f"{tid}: incoming_beat_alignment_target_ms={in_beat_target} is on beats_ms grid (nearest={d:.4f}ms, tolerance={GRID_TOLERANCE_MS}ms)")

        if in_downbeat_target is not None:
            d = nearest_distance_ms(in_downbeat_target, in_gt["downbeats_ms"])
            check(d <= GRID_TOLERANCE_MS, f"{tid}: incoming_downbeat_alignment_target_ms={in_downbeat_target} is on downbeats_ms grid (nearest={d:.4f}ms, tolerance={GRID_TOLERANCE_MS}ms)")

    print(f"\n{'ALL CHECKS PASS' if not failures else f'{len(failures)} CHECK(S) FAILED'}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
