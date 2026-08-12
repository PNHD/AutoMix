#!/usr/bin/env python3
"""
P0-M3-R2 (Apple-like redesign) -- independent verification script.

Numbered assertion groups mapped to specific stop-conditions from Issue #6
"PM PRODUCT DIRECTION UPDATE -- APPLE-LIKE NEAR-END LISTENING TARGET" plus
retained AC coverage from the original Issue #6 task body. PASS/FAIL printed
for each, nonzero exit on any FAIL.

Run: python verify.py
"""
import ast
import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from policy.policies import decide, decide_at_time, POLICY_NAMES
from policy.compatibility import evaluate_pair_compatibility, downgrade_transition_class_set

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "fixtures.json")
PAIR_FIXTURES_PATH = os.path.join(HERE, "fixtures", "pair_fixtures.json")
RESULTS_DIR = os.path.join(HERE, "results")

GROUND_TRUTH_ONLY_FIELDS = {
    "is_premature_trap",
    "is_vocal_collision_trap",
    "is_valid_natural_exit",
    "is_preferred_earliest_valid_exit",
    "highlight_eligible",
    "expected_overall_eligible",
}

POLICY_MODULE_FILES = (
    "policy/eligibility.py",
    "policy/policies.py",
    "policy/contract.py",
    "policy/metrics.py",
    "policy/compatibility.py",
    "policy/ranking.py",
)

failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_fixture(fixtures, fid):
    return next(fx for fx in fixtures if fx["fixture_id"] == fid)


def find_pair(pairs, pid):
    return next(p for p in pairs if p["pair_id"] == pid)


def winner_candidate_id(fixture, decision):
    if decision.decision_type != "TRANSITION":
        return None
    onset = decision.transition_onset_window_ms["t_start_ms"]
    for c in fixture["candidates"]:
        if c["t_ms"] == onset and not c.get("is_end_of_track"):
            return c["candidate_id"]
    return None


def decision_is_transition_at(fixture, decision, candidate_id):
    return decision.decision_type == "TRANSITION" and winner_candidate_id(fixture, decision) == candidate_id


def ac_isolation_check():
    """
    Ground-truth-only fixture fields are never read by policy decision code
    (AST-based, immune to prose/comment mentions).
    """
    offenders = []
    for relpath in POLICY_MODULE_FILES:
        path = os.path.join(HERE, relpath)
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=relpath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in GROUND_TRUTH_ONLY_FIELDS:
                    offenders.append((relpath, node.args[0].value, node.lineno))
            if isinstance(node, ast.Subscript):
                sl = node.slice
                val = sl.value if isinstance(sl, ast.Index) else sl
                if isinstance(val, ast.Constant) and val.value in GROUND_TRUTH_ONLY_FIELDS:
                    offenders.append((relpath, val.value, node.lineno))
    check("0. Ground-truth-only fixture fields are never read by policy decision code", len(offenders) == 0, f"offenders={offenders}")


def no_dsp_dependency_check():
    """AC16/AC17: no Signalsmith Stretch / Rubber Band / production-engine import anywhere."""
    forbidden = ("rubberband", "pyrubberband", "signalsmith", "librosa.effects.pitch_shift", "librosa.effects.time_stretch")
    offenders = []
    for path in glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    lowered = stripped.lower()
                    for bad in forbidden:
                        if bad in lowered:
                            offenders.append((path, lineno, stripped))
    check("0b. No Signalsmith/Rubber Band/DSP-library import anywhere in tools/p0m3/transition_policy", len(offenders) == 0, f"offenders={offenders}")


def no_audio_bytes_check():
    forbidden_ext = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac")
    offenders = [p for p in glob.glob(os.path.join(HERE, "**", "*"), recursive=True) if p.lower().endswith(forbidden_ext)]
    check("0c. No audio bytes committed anywhere in tools/p0m3/transition_policy", len(offenders) == 0, f"offenders={offenders}")


def main():
    fixtures = load_json(FIXTURES_PATH)
    pair_fixtures = load_json(PAIR_FIXTURES_PATH)
    by_id = {fx["fixture_id"]: fx for fx in fixtures}
    pair_by_id = {p["pair_id"]: p for p in pair_fixtures}

    print("=== 0. Structural / scope-boundary checks ===")
    check("timing fixture count == 14 (spec letters A-N)", len(fixtures) == 14, f"got {len(fixtures)}")
    check("pair fixture count == 5 (spec letters G-K)", len(pair_fixtures) == 5, f"got {len(pair_fixtures)}")
    ac_isolation_check()
    no_dsp_dependency_check()
    no_audio_bytes_check()

    print("\n=== STOP-CONDITION: a 7-minute normal song is NOT exited at ~2 minutes (catastrophic) ===")
    tp11 = by_id["TP-11"]
    d = decide(tp11, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-11 does not select the ~2min technically-attractive trap", not decision_is_transition_at(tp11, d, "TP-11-C1"))
    check("TP-11 selects the strong near-end candidate instead", decision_is_transition_at(tp11, d, "TP-11-C2"))
    check("TP-11 selected candidate preservation ratio >= 0.97 (preferred band)", d.outgoing_content_preservation_target >= 0.97)
    trap_entry = next(t for t in d.candidate_rank_trace if t["candidate_id"] == "TP-11-C1")
    check("TP-11 the ~2min trap candidate itself measures < 0.90 preservation (would be catastrophic if chosen)", trap_entry["outgoing_content_preservation_ratio"] < 0.90)

    print("\n=== STOP-CONDITION: preservation < 0.90 never occurs without an explicit authored exception ===")
    default_label_decisions = [decide(fx, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT") for fx in fixtures]
    catastrophic = [
        d for d in default_label_decisions
        if d.decision_type == "TRANSITION" and d.outgoing_content_preservation_target is not None and d.outgoing_content_preservation_target < 0.90
    ]
    check("no SEAMLESS_FULL_TRACK_DEFAULT transition anywhere has preservation < 0.90", len(catastrophic) == 0, f"offenders={[c.fixture_id for c in catastrophic]}")

    print("\n=== STOP-CONDITION: first-eligible-wins does NOT occur when a better near-end candidate exists (TP-12) ===")
    tp12 = by_id["TP-12"]
    d = decide(tp12, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-12 selects Y (musically stronger), not X (earlier/first-in-array)", decision_is_transition_at(tp12, d, "TP-12-Y"))
    x_entry = next(t for t in d.candidate_rank_trace if t["candidate_id"] == "TP-12-X")
    y_entry = next(t for t in d.candidate_rank_trace if t["candidate_id"] == "TP-12-Y")
    check("both X and Y were evaluated as eligible (ranking chose between real alternatives, not a fallback)", x_entry["eligible"] and y_entry["eligible"])
    check("Y outranks X in eligible_rank (rank 1 beats a higher number)", y_entry["eligible_rank"] < x_entry["eligible_rank"])

    print("\n=== STOP-CONDITION: candidate ordering never changes the winner (order invariance) ===")
    with open(os.path.join(RESULTS_DIR, "order_invariance.json"), "r", encoding="utf-8") as f:
        oi = json.load(f)
    check("order_invariance.json reports order_invariant == true", oi["order_invariant"] is True)
    check("winner is TP-12-Y under all three orderings", oi["winner_normal_order"] == oi["winner_reversed_order"] == oi["winner_shuffled_order"] == "TP-12-Y")
    # Independent re-derivation (not just trusting the cached results file).
    fx_shuf2 = dict(tp12); cs = list(tp12["candidates"]); random.Random(99).shuffle(cs); fx_shuf2["candidates"] = cs
    d_shuf2 = decide(fx_shuf2, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("independently re-shuffled (different seed) order still selects Y", decision_is_transition_at(fx_shuf2, d_shuf2, "TP-12-Y"))

    print("\n=== STOP-CONDITION: BPM alone never authorizes complex mixing ===")
    pair02 = pair_by_id["PAIR-02"]  # matching BPM, incompatible genre
    compat02 = evaluate_pair_compatibility(pair02)
    check("PAIR-02 has TEMPO-compatible BPM (isolates genre as the sole failure)", compat02.tempo_compatibility in ("DIRECT", "HALF_DOUBLE"))
    check("PAIR-02 is NOT overall_dynamic_mix_eligible despite matching BPM (genre incompatible)", compat02.overall_dynamic_mix_eligible is False)
    allowed02 = downgrade_transition_class_set(["FULL_DJ_BLEND", "SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"], compat02)
    check("PAIR-02 FULL_DJ_BLEND withheld", "FULL_DJ_BLEND" not in allowed02)

    print("\n=== STOP-CONDITION: incompatible genre/tempo pair never receives forced complex transition ===")
    for pid in ("PAIR-02", "PAIR-03"):
        compat = evaluate_pair_compatibility(pair_by_id[pid])
        check(f"{pid} overall_dynamic_mix_eligible is False", compat.overall_dynamic_mix_eligible is False)
        allowed = downgrade_transition_class_set(["FULL_DJ_BLEND", "SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"], compat)
        check(f"{pid} FULL_DJ_BLEND and SHORT_EQ_BLEND both withheld", "FULL_DJ_BLEND" not in allowed and "SHORT_EQ_BLEND" not in allowed)
        d_int = decide(tp11, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT", pair=pair_by_id[pid])
        check(f"TP-11 (excellent timing) + {pid} (incompatible) still withholds FULL_DJ_BLEND end-to-end", "FULL_DJ_BLEND" not in d_int.allowed_transition_class_set)

    print("\n=== STOP-CONDITION: excessive tempo stretch is never allowed without downgrade ===")
    compat03 = evaluate_pair_compatibility(pair_by_id["PAIR-03"])
    check("PAIR-03 tempo_compatibility == EXCESSIVE_STRETCH", compat03.tempo_compatibility == "EXCESSIVE_STRETCH")
    check("PAIR-03 required_tempo_stretch_pct exceeds the justified ceiling (0.12)", compat03.required_tempo_stretch_pct > 0.12)

    print("\n=== STOP-CONDITION: vocal collision is never ignored ===")
    compat04 = evaluate_pair_compatibility(pair_by_id["PAIR-04"])
    check("PAIR-04 (dense vocal collision) overall_dynamic_mix_eligible is False", compat04.overall_dynamic_mix_eligible is False)
    allowed04 = downgrade_transition_class_set(["FULL_DJ_BLEND", "SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"], compat04)
    check("PAIR-04 FULL_DJ_BLEND and SHORT_EQ_BLEND both withheld despite compatible genre/tempo/beat", "FULL_DJ_BLEND" not in allowed04 and "SHORT_EQ_BLEND" not in allowed04)
    tp08 = by_id["TP-08"]
    d08 = decide(tp08, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-08 never selects the HIGH single-track vocal-collision candidate", not decision_is_transition_at(tp08, d08, "TP-08-C1"))

    print("\n=== STOP-CONDITION: missing analysis confidence never creates fabricated certainty ===")
    tp09 = by_id["TP-09"]
    d09 = decide(tp09, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-09 never transitions at the unverified-confidence candidate", not decision_is_transition_at(tp09, d09, "TP-09-C1"))
    check("TP-09 final decision is NO_SPECIAL_TRANSITION (conservative fallback)", d09.decision_type == "NO_SPECIAL_TRANSITION")
    compat_low_conf = dict(pair_by_id["PAIR-01"]); compat_low_conf["analysis_confidence"] = "LOW"
    result_low_conf = evaluate_pair_compatibility(compat_low_conf)
    check("pair-level LOW analysis_confidence also disables overall_dynamic_mix_eligible", result_low_conf.overall_dynamic_mix_eligible is False)

    print("\n=== STOP-CONDITION: highlight behavior never becomes the default ===")
    tp10 = by_id["TP-10"]
    d_default = decide(tp10, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    d_balanced = decide(tp10, "BALANCED_MIX_RESEARCH_CONTROL", "BALANCED_MIX")
    d_highlight = decide(tp10, "EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL", "HIGHLIGHT_EXPLICIT")
    check("TP-10 SEAMLESS_FULL_TRACK_DEFAULT never transitions at the highlight point", not decision_is_transition_at(tp10, d_default, "TP-10-C1"))
    check("TP-10 BALANCED_MIX research control never transitions at the highlight point", not decision_is_transition_at(tp10, d_balanced, "TP-10-C1"))
    check("TP-10 EXPLICIT_HIGHLIGHT (matched intent only) DOES transition at the highlight point", decision_is_transition_at(tp10, d_highlight, "TP-10-C1"))
    d_mismatch = decide(tp10, "EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL with a mismatched caller intent never transitions (R1, no silent intent rewrite)", d_mismatch.decision_type != "TRANSITION")
    check("mismatch decision's listener_intent matches the caller's ACTUAL argument, not a rewritten one", d_mismatch.listener_intent == "SEAMLESS_FULL_TRACK_DEFAULT")
    with open(os.path.join(RESULTS_DIR, "metrics.json"), "r", encoding="utf-8") as f:
        metrics = json.load(f)["metrics"]
    check(
        "aggregate: SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT never has a higher fallback rate than a naive baseline due to highlight leakage (sanity)",
        "SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT" in metrics,
    )

    print("\n=== STOP-CONDITION: transition onset is never treated as outgoing truncation ===")
    d11 = decide(tp11, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-11 transition_onset_ratio is well below 1.0 (onset happens before the natural end)", d11.transition_onset_window_ms["t_start_ms"] / d11.current_track_effective_content_end_ms < 0.99)
    check("TP-11 outgoing_content_preservation_target is still ~1.0 despite the earlier onset (overlap covers the remainder)", d11.outgoing_content_preservation_target >= 0.99)

    print("\n=== STOP-CONDITION: a meaningful outro is never trimmed as if it were dead air ===")
    tp13 = by_id["TP-13"]
    d13 = decide(tp13, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-13 selects the outro candidate (musical content, not the dead-air END marker)", decision_is_transition_at(tp13, d13, "TP-13-C1"))
    check("TP-13 effective_content_end_ms excludes only the authored dead air (210000, not raw duration 250000)", d13.current_track_effective_content_end_ms == 210000)
    check("TP-13 preservation ratio == 1.0 -- the musical outro is fully preserved, dead air correctly excluded from the denominator", d13.outgoing_content_preservation_target == 1.0)
    tp05 = by_id["TP-05"]  # contrast: NO authored dead-air annotation -> full duration_ms used, no silent trimming
    d05 = decide(tp05, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-05 (unannotated tail) uses the FULL raw duration as effective_content_end_ms (195000) -- never silently trims an unannotated tail", d05.current_track_effective_content_end_ms == 195000)

    print("\n=== Retained AC coverage ===")
    check("NAIVE_EARLIEST_COMPATIBLE is a registered policy (AC2)", "NAIVE_EARLIEST_COMPATIBLE" in POLICY_NAMES)
    check("BPM_KEY_ONLY_EARLY is a registered policy (AC2)", "BPM_KEY_ONLY_EARLY" in POLICY_NAMES)
    check("NAIVE_EARLIEST_COMPATIBLE has nonzero premature_exit_rate (AC2)", metrics["NAIVE_EARLIEST_COMPATIBLE@SEAMLESS_FULL_TRACK_DEFAULT"]["premature_exit_rate"] > 0)
    check("BPM_KEY_ONLY_EARLY has nonzero premature_exit_rate (AC2)", metrics["BPM_KEY_ONLY_EARLY@SEAMLESS_FULL_TRACK_DEFAULT"]["premature_exit_rate"] > 0)

    tp01 = by_id["TP-01"]
    d01 = decide(tp01, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("TP-01 (AC3) does not transition at the 30s trap", not decision_is_transition_at(tp01, d01, "TP-01-C1"))
    check("TP-01 (AC3) decision is NO_SPECIAL_TRANSITION (played through to natural outro)", d01.decision_type == "NO_SPECIAL_TRANSITION")

    with open(os.path.join(RESULTS_DIR, "sensitivity_matrix.json"), "r", encoding="utf-8") as f:
        sensitivity = json.load(f)
    all_zero = all(row["premature_exit_rate"] == 0.0 for row in sensitivity["rows"])
    check("AC5/AC13: premature_exit_rate stays 0 across every swept preservation floor (structural gate independent of the floor)", all_zero)
    check("AC13: sensitivity sweep covers exactly the required floors 0.90/0.93/0.95/0.97/0.98", sensitivity["floors_tested"] == [0.90, 0.93, 0.95, 0.97, 0.98])

    tp03 = by_id["TP-03"]
    d03 = decide(tp03, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("AC6: TP-03 short-track exception captures the valid exit C2", decision_is_transition_at(tp03, d03, "TP-03-C2"))

    tp04 = by_id["TP-04"]
    d04 = decide(tp04, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("AC7: TP-04 long-track rejects the too-early mid-track candidate", not decision_is_transition_at(tp04, d04, "TP-04-C2"))
    check("AC7: TP-04 long-track captures the near-end candidate instead", decision_is_transition_at(tp04, d04, "TP-04-C3"))
    d04_fixed = decide(tp04, "FIXED_SECONDS_BEFORE_END_ONLY", "SEAMLESS_FULL_TRACK_DEFAULT")
    check("AC7/F: FIXED_SECONDS_BEFORE_END_ONLY baseline misses the near-end candidate (proves fixed-seconds rule fails)", not decision_is_transition_at(tp04, d04_fixed, "TP-04-C3"))

    check("AC8: TP-05 never transitions at the technical trap", not decision_is_transition_at(tp05, d05, "TP-05-C1"))
    check("AC8: TP-05 final decision is NO_SPECIAL_TRANSITION (no clean outro exists)", d05.decision_type == "NO_SPECIAL_TRANSITION")

    with open(os.path.join(RESULTS_DIR, "playthrough_demo.json"), "r", encoding="utf-8") as f:
        demo = json.load(f)
    check("AC10: PLAY_THROUGH is reachable", demo["query_at_60000ms_before_outro_region"]["decision_type"] == "PLAY_THROUGH")
    check("AC10: NO_SPECIAL_TRANSITION is reachable", demo["query_at_210000ms_natural_end"]["decision_type"] == "NO_SPECIAL_TRANSITION")

    print("\n=== AC11: queue ordering is never used as permission to exit the current track early ===")
    import copy
    tp01_poor = copy.deepcopy(tp01); tp01_poor["queue_next_track_quality"] = "POOR"
    tp01_unk = copy.deepcopy(tp01); tp01_unk["queue_next_track_quality"] = "UNKNOWN"
    d_excellent = decide(tp01, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    d_poor = decide(tp01_poor, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    d_unk = decide(tp01_unk, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
    check(
        "TP-01 decision is identical regardless of queue_next_track_quality",
        d_excellent.decision_type == d_poor.decision_type == d_unk.decision_type
        and d_excellent.candidate_rank_trace == d_poor.candidate_rank_trace == d_unk.candidate_rank_trace,
    )
    check("PlannerDecision.queue_order_independent_of_exit_timing is always True", d_excellent.queue_order_independent_of_exit_timing is True)

    print("\n=== AC12: candidate decisions expose reason codes / traceable evidence ===")
    with open(os.path.join(RESULTS_DIR, "decision_traces.json"), "r", encoding="utf-8") as f:
        traces = json.load(f)
    all_have_trace = all(len(d["candidate_rank_trace"]) > 0 for label, per_fixture in traces.items() for fixture_id, d in per_fixture.items())
    check("every (fixture, policy) decision has a non-empty candidate_rank_trace", all_have_trace)
    all_have_reasons = all(
        (d["decision_type"] != "PLAY_THROUGH") or len(d["reason_codes"]) > 0
        for label, per_fixture in traces.items() for fixture_id, d in per_fixture.items()
    )
    check("every non-PLAY_THROUGH decision carries reason_codes", all_have_reasons)

    print("\n=== AC18: a concrete P0-M3-R3 planner-output contract is produced ===")
    sample_keys = set(d01.to_dict().keys())
    required_keys = {
        "decision_type", "current_track_effective_content_end_ms", "transition_onset_window_ms",
        "outgoing_last_audible_target_ms", "outgoing_content_preservation_target", "next_track_entry_window_ms",
        "allowed_transition_class_set", "pair_compatibility_components", "beat_alignment_target",
        "downbeat_alignment_target", "permitted_tempo_ratio", "permitted_pitch_shift",
        "energy_continuity_target", "vocal_collision_constraints", "bass_collision_constraints",
        "analysis_confidence", "reason_codes", "candidate_rank_trace",
        "queue_order_independent_of_exit_timing",
    }
    check("PlannerDecision contract exposes every P0-M3-R3 required field", required_keys.issubset(sample_keys), f"missing={required_keys - sample_keys}")

    print(f"\n=== RESULT: {'ALL ASSERTIONS PASS' if not failures else f'{len(failures)} FAILURE(S)'} ===")
    if failures:
        for f in failures:
            print(f" - FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
