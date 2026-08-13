"""
P0-M3-R3 STAGE-B EVIDENCE AUDIT REPAIR (B2/B4/B6) -- shared, pure,
file-I/O-free pair-gate classification used by BOTH
`compute_pair_gate_calibration.py` (aggregate calibration evidence) and
`select_real_music_pairs.py` (near-miss forensics embedded in the
selection trace), so the two never compute gate pass/fail with two
different, potentially-divergent implementations.

Classifies each independent R2 hard-gate dimension into exactly one of:
  PASS
  MEASURED_INCOMPATIBLE  -- a real measurement was taken and it failed
  UNKNOWN_EVIDENCE       -- the gate failed because trustworthy evidence
                            was insufficient/absent, NOT because
                            incompatibility was proven
Never conflates the two (Issue #7 PM STAGE-B EVIDENCE AUDIT REPAIR B5:
"67/100 tracks having no trustworthy local genre evidence is not proof
that those tracks have incompatible genres").
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

import select_real_music_pairs as selector  # noqa: E402
from policy.compatibility import evaluate_pair_compatibility, _tempo_relation  # noqa: E402

GATE_ORDER = ["genre", "tempo", "beat", "downbeat", "harmonic", "structure", "texture", "vocal", "bass", "analysis_confidence"]
CONFIDENCE_LEDGER_DIAGNOSTIC_GATE_ORDER = [g for g in GATE_ORDER if g != "analysis_confidence"]

PASS = "PASS"
MEASURED_INCOMPATIBLE = "MEASURED_INCOMPATIBLE"
UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"


def classify_pair(out_a: dict, in_a: dict):
    """Returns (compat_input, compat, gate_status: dict[str,str], failed_gates: list[str])."""
    ci = selector.build_pair_compat_input(out_a, in_a)
    compat = evaluate_pair_compatibility({**ci})

    gate_status = {}
    gate_status["genre"] = (
        PASS if compat.genre_compatibility == "COMPATIBLE"
        else (UNKNOWN_EVIDENCE if (not ci["outgoing"]["genre_tags"] or not ci["incoming"]["genre_tags"]) else MEASURED_INCOMPATIBLE)
    )
    gate_status["tempo"] = PASS if compat.tempo_compatibility in ("DIRECT", "HALF_DOUBLE") else MEASURED_INCOMPATIBLE
    gate_status["beat"] = PASS if compat.beat_compatibility == "SUFFICIENT" else UNKNOWN_EVIDENCE
    gate_status["downbeat"] = PASS if compat.downbeat_compatibility == "SUFFICIENT" else UNKNOWN_EVIDENCE
    gate_status["harmonic"] = (
        PASS if compat.harmonic_compatibility == "COMPATIBLE"
        else (UNKNOWN_EVIDENCE if compat.harmonic_compatibility == "UNKNOWN" else MEASURED_INCOMPATIBLE)
    )
    # Structure has no "measured incompatible" state in this design -- a
    # boundary either has independent structural evidence (instrumental
    # tail / novelty peak) or it does not; absence is never proof of an
    # actual structural mismatch.
    gate_status["structure"] = PASS if ci["structure_compatibility"] == "COMPATIBLE" else UNKNOWN_EVIDENCE
    # Texture/vocal/bass are always MEASURED (never unknown) in this
    # analyzer -- a failure here is a real measured gap/risk.
    gate_status["texture"] = PASS if ci["intro_outro_texture_compatible"] else MEASURED_INCOMPATIBLE
    gate_status["vocal"] = PASS if ci["vocal_collision_risk"] not in ("HIGH", "MEDIUM") else MEASURED_INCOMPATIBLE
    gate_status["bass"] = PASS if ci["bass_percussion_collision_risk"] != "HIGH" else MEASURED_INCOMPATIBLE
    gate_status["analysis_confidence"] = PASS if ci["analysis_confidence"] == "HIGH" else UNKNOWN_EVIDENCE

    failed_gates = [g for g in GATE_ORDER if gate_status[g] != PASS]
    return ci, compat, gate_status, failed_gates


def confidence_ledger_diagnostic(gate_status: dict) -> dict:
    """A1 diagnostic verdict with no duplicate aggregate-confidence gate.

    Every underlying load-bearing lane remains required.  Only the legacy
    ``analysis_confidence=min(structure, genre, harmonic)`` aggregate is
    omitted because those same three lanes are already represented directly.
    This function is research-only and never calls or modifies the R2 policy.
    """
    failed = [g for g in CONFIDENCE_LEDGER_DIAGNOSTIC_GATE_ORDER if gate_status[g] != PASS]
    return {
        "gate_order": CONFIDENCE_LEDGER_DIAGNOSTIC_GATE_ORDER,
        "eligible": not failed,
        "failed_gates": failed,
        "aggregate_analysis_confidence_counted_as_independent": False,
    }


def iter_tempo_eligible_pairs(analysis: dict, lo: float, hi: float):
    """Yields (out_id, in_id, relation, stretch_pct, ratio) for every ordered
    pair whose tempo relation is DIRECT/HALF_DOUBLE and deviation in [lo, hi]."""
    ids = sorted(analysis.keys())
    for out_id in ids:
        out_a = analysis[out_id]
        for in_id in ids:
            if out_id == in_id:
                continue
            in_a = analysis[in_id]
            relation, stretch_pct, ratio, _requires_change = _tempo_relation(out_a["tempo"]["bpm"], in_a["tempo"]["bpm"])
            if relation in ("DIRECT", "HALF_DOUBLE") and lo <= stretch_pct <= hi:
                yield out_id, in_id, relation, stretch_pct, ratio


GATE_TO_TRISTATE = {"PASS": "COMPATIBLE", "MEASURED_INCOMPATIBLE": "INCOMPATIBLE", "UNKNOWN_EVIDENCE": "UNKNOWN"}


def entry_evidence_label(in_a: dict) -> str:
    c = in_a["candidates"]
    if c["entry_is_authored_silence_skip"]:
        return "AUTHORED_SILENCE_SKIP"
    if c["entry_has_detected_intro"]:
        return "INSTRUMENTAL_LEAD_DETECTED"
    if abs(c["entry_candidate_t_ms"]) < 1.0:
        return "TRACK_START"
    return "UNEVIDENCED_NONZERO"  # should not occur by construction; flagged honestly if it ever does


def near_miss_entry(r: dict) -> dict:
    ci, compat = r["compat_input"], r["compat"]
    out_a, in_a = r["out_a"], r["in_a"]
    preservation_ratio = out_a["candidates"]["exit_candidate_t_ms"] / max(out_a["duration_ms"], 1.0)
    return {
        "outgoing_opaque_id": r["out_id"],
        "incoming_opaque_id": r["in_id"],
        "tempo_deviation_pct": round(r["stretch_pct"] * 100, 2),
        "preservation_ratio": round(preservation_ratio, 4),
        "incoming_entry_evidence": entry_evidence_label(in_a),
        "genre_result": GATE_TO_TRISTATE[r["gate_status"]["genre"]],
        "beat_result": GATE_TO_TRISTATE[r["gate_status"]["beat"]],
        "downbeat_result": GATE_TO_TRISTATE[r["gate_status"]["downbeat"]],
        "structure_result": GATE_TO_TRISTATE[r["gate_status"]["structure"]],
        "texture_result": GATE_TO_TRISTATE[r["gate_status"]["texture"]],
        "vocal_result": GATE_TO_TRISTATE[r["gate_status"]["vocal"]],
        "bass_percussion_result": GATE_TO_TRISTATE[r["gate_status"]["bass"]],
        "harmonic_result": GATE_TO_TRISTATE[r["gate_status"]["harmonic"]],
        "analysis_confidence_result": GATE_TO_TRISTATE[r["gate_status"]["analysis_confidence"]],
        "energy_continuity_bucket": ci["_energy_continuity_bucket"],
        "projected_loudness_gap_db": ci["_projected_loudness_gap_db"],
        "projected_bass_gap_db": ci["_projected_bass_gap_db"],
        "combined_energy_gap_db": ci["_combined_energy_gap_db"],
        "failed_hard_gate_count": len(r["failed_gates"]),
        "failed_gates": r["failed_gates"],
        "reason_codes": compat.reason_codes,
    }


def rank_near_misses(records: list[dict], top_n: int = 10) -> list[dict]:
    """Ranked first by FEWEST independently failed gates, then by
    preservation ratio (higher better) and combined energy gap (smaller
    better) as secondary quality tie-breaks, opaque IDs last. Computed
    BEFORE any final hard-gate rejection -- these are exactly the
    candidates the pool filter excluded, kept here purely for forensic
    visibility (no rendering, no listening)."""
    def key(r):
        out_a = r["out_a"]
        preservation_ratio = out_a["candidates"]["exit_candidate_t_ms"] / max(out_a["duration_ms"], 1.0)
        return (len(r["failed_gates"]), -preservation_ratio, r["compat_input"]["_combined_energy_gap_db"], r["out_id"], r["in_id"])

    ranked = sorted(records, key=key)[:top_n]
    return [near_miss_entry(r) for r in ranked]


def audit_universe(analysis: dict, lo: float, hi: float):
    """Full audit of one tempo-eligible universe. Returns list of per-pair
    audit records (dicts) -- no rendering, no I/O beyond reading `analysis`."""
    records = []
    for out_id, in_id, relation, stretch_pct, ratio in iter_tempo_eligible_pairs(analysis, lo, hi):
        out_a, in_a = analysis[out_id], analysis[in_id]
        ci, compat, gate_status, failed_gates = classify_pair(out_a, in_a)
        records.append({
            "out_id": out_id, "in_id": in_id, "relation": relation,
            "stretch_pct": stretch_pct, "ratio": ratio,
            "compat_input": ci, "compat": compat,
            "gate_status": gate_status, "failed_gates": failed_gates,
            "out_a": out_a, "in_a": in_a,
        })
    return records
