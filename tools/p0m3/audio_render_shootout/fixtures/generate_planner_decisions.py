"""
Generates the REAL R2 PlannerDecision for each P0-M3-R3 scenario by calling
the accepted tools/p0m3/transition_policy planner directly -- never
hand-fabricating a PlannerDecision-shaped dict (Issue #7: "Renderer MUST
consume the accepted R2 PlannerDecision... Do NOT silently select a
different outgoing exit / incoming entry / transition class / tempo ratio /
pitch correction").

Usage:
    python fixtures/generate_planner_decisions.py

Writes fixtures/planner_decisions/<scenario_id>.json (committed).
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
TRANSITION_POLICY_ROOT = REPO_ROOT / "tools" / "p0m3" / "transition_policy"
assert TRANSITION_POLICY_ROOT.is_dir(), f"expected {TRANSITION_POLICY_ROOT} to exist"

sys.path.insert(0, str(TRANSITION_POLICY_ROOT))
sys.path.insert(0, str(HERE))

from policy.boundary import plan_transition_boundary  # noqa: E402
from policy.eligibility import SEAMLESS_FULL_TRACK_DEFAULT  # noqa: E402

from scenario_fixtures import ALL_SCENARIOS  # noqa: E402

OUT_DIR = HERE / "planner_decisions"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    summary = []
    for scenario in ALL_SCENARIOS:
        decision = plan_transition_boundary(scenario, SEAMLESS_FULL_TRACK_DEFAULT)
        decision_dict = asdict(decision)
        out_path = OUT_DIR / f"{scenario['transition_id']}.json"
        out_path.write_text(json.dumps(decision_dict, indent=2), encoding="utf-8")
        summary.append({
            "transition_id": scenario["transition_id"],
            "decision_type": decision.decision_type,
            "allowed_transition_class_set": decision.allowed_transition_class_set,
            "selected_outgoing_exit_candidate_id": decision.selected_outgoing_exit_candidate_id,
            "selected_incoming_entry_candidate_id": decision.selected_incoming_entry_candidate_id,
            "outgoing_content_preservation_target": decision.outgoing_content_preservation_target,
            "required_tempo_ratio": decision.required_tempo_ratio,
            "tempo_requires_playback_rate_change": (
                decision.pair_compatibility_components.get("tempo_requires_playback_rate_change")
                if decision.pair_compatibility_components else None
            ),
            "required_pitch_shift_semitones": decision.required_pitch_shift_semitones,
            "beat_alignment_action": decision.beat_alignment_action,
            "bar_alignment_action": decision.bar_alignment_action,
            "outgoing_beat_alignment_target_ms": decision.outgoing_beat_alignment_target_ms,
            "incoming_beat_alignment_target_ms": decision.incoming_beat_alignment_target_ms,
        })
        print(f"{scenario['transition_id']}: decision_type={decision.decision_type} "
              f"classes={decision.allowed_transition_class_set} "
              f"tempo_ratio={decision.required_tempo_ratio} "
              f"pitch_semitones={decision.required_pitch_shift_semitones}")

    (OUT_DIR / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {len(ALL_SCENARIOS)} planner decisions to {OUT_DIR}")


if __name__ == "__main__":
    main()
