"""P0-M3-R3 RM041<->RM014 evidence stability -- A9 analysis_confidence counterfactual.

Read-only counterfactual against the UNMODIFIED
``tools/p0m3/transition_policy/policy/compatibility.py`` semantics. This
script imports ``evaluate_pair_compatibility`` without changing it and
without changing ``select_real_music_pairs.py``.

The accepted RM041->RM014 pair-compatibility INPUT is reconstructed from
the exact, already-committed strict reason codes in
``tools/p0m3/all_in_one_runtime_probe/real_evidence/results/three_pair_replay_sanitized.json``
(``strict_reason_codes_unchanged``) plus the already-committed public BPM
values (RM041=103, RM014=105, from
``docs/research/P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE.md``'s four-track table).
Genre TAG TEXT itself is private and was never committed anywhere -- this
script therefore uses a placeholder tag pair from the SAME compatible
family (``COMPATIBLE_GENRE_FAMILIES["pop_rock"]``) purely to reproduce the
identical GENRE_COMPATIBLE_SAME_FAMILY decision surface. This is an
explicitly labelled SYNTHETIC_RECONSTRUCTION for counterfactual diagnostic
purposes only -- it is not a claim about the real private tag content, and
it is verified below to reproduce the exact accepted CASE 0 reason-code
set byte-for-byte before any counterfactual case is computed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

from policy.compatibility import evaluate_pair_compatibility  # noqa: E402

ACCEPTED_STRICT_REASON_CODES_CASE0 = [
    "GENRE_COMPATIBLE_SAME_FAMILY",
    "TEMPO_DIRECT_COMPATIBLE",
    "BEAT_CONFIDENCE_SUFFICIENT",
    "DOWNBEAT_CONFIDENCE_INSUFFICIENT",
    "HARMONIC_UNKNOWN",
    "HARMONIC_UNKNOWN_DOWNGRADED",
    "ENERGY_CONTINUITY_STRONG",
    "STRUCTURE_UNKNOWN",
    "STRUCTURE_COMPATIBILITY_REQUIRED_FOR_FULL_DJ",
    "VOCAL_COLLISION_RISK_ACCEPTABLE",
    "BASS_PERCUSSION_COLLISION_RISK_ACCEPTABLE",
    "INTRO_OUTRO_TEXTURE_COMPATIBLE",
    "ANALYSIS_CONFIDENCE_LOW_PAIR",
]

BASE_PAIR = {
    "outgoing": {"genre_tags": ["pop"], "bpm": 103},
    "incoming": {"genre_tags": ["pop"], "bpm": 105},
    "beat_confidence": "HIGH",
    "downbeat_confidence": "MEDIUM",  # any value below HIGH reproduces DOWNBEAT_CONFIDENCE_INSUFFICIENT
    "harmonic_relationship": None,
    "energy_continuity": "STRONG",
    "structure_compatibility": "UNKNOWN",
    "vocal_collision_risk": "LOW",
    "bass_percussion_collision_risk": "LOW",
    "intro_outro_texture_compatible": True,
    "analysis_confidence": "LOW",
}


def min_conf(*vals):
    order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    return min(vals, key=lambda v: order.get(v, 0))


def build_case(case_id: str, description: str, *, harmonic_high: bool, structure_high: bool) -> dict:
    pair = dict(BASE_PAIR)
    genre_strength = "HIGH"  # already available/HIGH per the accepted evidence and task statement
    structure_strength = "HIGH" if structure_high else "LOW"
    harmonic_strength = "HIGH" if harmonic_high else "LOW"

    if harmonic_high:
        pair["harmonic_relationship"] = "COMPATIBLE"
    else:
        pair["harmonic_relationship"] = None

    if structure_high:
        pair["structure_compatibility"] = "COMPATIBLE"
    else:
        pair["structure_compatibility"] = "UNKNOWN"

    pair["analysis_confidence"] = min_conf(structure_strength, genre_strength, harmonic_strength)

    compat = evaluate_pair_compatibility(pair)

    remaining_hard_gates = []
    if compat.genre_compatibility != "COMPATIBLE":
        remaining_hard_gates.append("genre")
    if compat.tempo_compatibility not in ("DIRECT", "HALF_DOUBLE"):
        remaining_hard_gates.append("tempo")
    if compat.beat_compatibility != "SUFFICIENT":
        remaining_hard_gates.append("beat")
    if compat.downbeat_compatibility != "SUFFICIENT":
        remaining_hard_gates.append("downbeat")
    if compat.structure_compatibility != "COMPATIBLE":
        remaining_hard_gates.append("structure")
    if compat.intro_outro_texture_compatibility != "COMPATIBLE":
        remaining_hard_gates.append("texture")
    if compat.vocal_collision_risk in ("HIGH", "MEDIUM"):
        remaining_hard_gates.append("vocal")
    if compat.bass_percussion_collision_risk == "HIGH":
        remaining_hard_gates.append("bass")
    if compat.analysis_confidence != "HIGH":
        remaining_hard_gates.append("analysis_confidence")
    if not (compat.harmonic_compatibility == "COMPATIBLE" or compat.harmonic_exception_applied):
        remaining_hard_gates.append("harmonic")

    return {
        "case_id": case_id,
        "description": description,
        "harmonic_assumed_defensibly_high": harmonic_high,
        "structure_assumed_defensibly_high": structure_high,
        "pair_compatibility": compat.to_dict(),
        "remaining_hard_gates": remaining_hard_gates,
        "strict_full_dj_eligible_if_legitimately_resolved": compat.overall_dynamic_mix_eligible,
    }


def main() -> int:
    case0 = build_case(
        "CASE_0_CURRENT_ACCEPTED_EVIDENCE",
        "Current accepted evidence, unchanged.",
        harmonic_high=False,
        structure_high=False,
    )
    reproduced = sorted(case0["pair_compatibility"]["reason_codes"])
    expected = sorted(ACCEPTED_STRICT_REASON_CODES_CASE0)
    if reproduced != expected:
        raise ValueError(
            "SYNTHETIC_RECONSTRUCTION_DID_NOT_REPRODUCE_ACCEPTED_CASE0_REASON_CODES: "
            f"got={reproduced} expected={expected}"
        )

    cases = [
        case0,
        build_case(
            "CASE_1_ONLY_HARMONIC_HIGH",
            "Only harmonic becomes defensibly HIGH (hypothetical).",
            harmonic_high=True,
            structure_high=False,
        ),
        build_case(
            "CASE_2_ONLY_STRUCTURE_HIGH",
            "Only structure becomes defensibly HIGH (hypothetical).",
            harmonic_high=False,
            structure_high=True,
        ),
        build_case(
            "CASE_3_HARMONIC_AND_STRUCTURE_HIGH",
            "Harmonic AND structure both become defensibly HIGH (hypothetical).",
            harmonic_high=True,
            structure_high=True,
        ),
    ]

    output = {
        "schema_version": 1,
        "scope": "RM041 -> RM014 ONLY",
        "note": "COUNTERFACTUAL DIAGNOSTIC ONLY. Does not mutate canonical evidence, "
                "compatibility.py, or select_real_music_pairs.py. Does not declare a "
                "render candidate. downbeat is never assumed resolved in any case "
                "(BeatNet ownership unchanged, no gate mutation).",
        "case0_reproduces_accepted_reason_codes_exactly": True,
        "cases": cases,
    }

    out_path = HERE / "results" / "counterfactual_matrix.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    for case in cases:
        print(
            f"{case['case_id']}: analysis_confidence={case['pair_compatibility']['analysis_confidence']} "
            f"remaining_hard_gates={case['remaining_hard_gates']} "
            f"strict_full_dj_eligible={case['strict_full_dj_eligible_if_legitimately_resolved']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
