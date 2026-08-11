#!/usr/bin/env python3
"""
P0-M3-R2 -- independent verification script. Mirrors the P0-M3-R1
verify_repair.py pattern: numbered assertion groups mapped to specific
acceptance criteria, PASS/FAIL printed for each, nonzero exit on any FAIL.

Run: python verify.py
"""
import ast
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from policy.policies import decide, decide_at_time, POLICY_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "fixtures.json")
RESULTS_DIR = os.path.join(HERE, "results")

GROUND_TRUTH_ONLY_FIELDS = {
    "is_premature_trap",
    "is_vocal_collision_trap",
    "is_valid_natural_exit",
    "is_preferred_earliest_valid_exit",
    "highlight_eligible",
}

failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def load_fixtures():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def find_fixture(fixtures, fid):
    return next(fx for fx in fixtures if fx["fixture_id"] == fid)


def find_candidate(fixture, cid):
    return next(c for c in fixture["candidates"] if c["candidate_id"] == cid)


def decision_is_transition_at(decision, candidate_id):
    return decision.decision_type == "TRANSITION" and decision.candidate_trace[-1]["candidate_id"] == candidate_id


def ac_isolation_check():
    """
    AC-supporting structural check: policy/eligibility.py and
    policy/policies.py never read a ground-truth-only field via
    candidate.get("...") / candidate["..."] as an actual code expression
    (comments/docstrings are not part of the AST, so this check is immune
    to prose mentioning the field names for documentation purposes).
    """
    offenders = []
    for relpath in ("policy/eligibility.py", "policy/policies.py", "policy/contract.py"):
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
    check(
        "0. Ground-truth-only fixture fields are never read by policy decision code (AC12 evidence integrity)",
        len(offenders) == 0,
        f"offenders={offenders}",
    )


def no_dsp_dependency_check():
    """AC16/AC17: no Signalsmith Stretch / Rubber Band / production-engine import anywhere in this package."""
    forbidden_import_substrings = ("rubberband", "pyrubberband", "signalsmith", "librosa.effects.pitch_shift", "librosa.effects.time_stretch")
    offenders = []
    for path in glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    lowered = stripped.lower()
                    for bad in forbidden_import_substrings:
                        if bad in lowered:
                            offenders.append((path, lineno, stripped))
    check("0b. No Signalsmith/Rubber Band/DSP-library import anywhere in tools/p0m3/transition_policy", len(offenders) == 0, f"offenders={offenders}")


def no_audio_bytes_check():
    forbidden_ext = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac")
    offenders = [p for p in glob.glob(os.path.join(HERE, "**", "*"), recursive=True) if p.lower().endswith(forbidden_ext)]
    check("0c. No audio bytes committed anywhere in tools/p0m3/transition_policy (AC15)", len(offenders) == 0, f"offenders={offenders}")


def main():
    fixtures = load_fixtures()

    print("=== 0. Structural / scope-boundary checks ===")
    check("fixture count == 10 (Task D minimum)", len(fixtures) == 10, f"got {len(fixtures)}")
    ac_isolation_check()
    no_dsp_dependency_check()
    no_audio_bytes_check()

    print("\n=== AC1: normal/default listening never silently equals highlight shortening (TP-10) ===")
    tp10 = find_fixture(fixtures, "TP-10")
    default_decision = decide(tp10, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    balanced_decision = decide(tp10, "STRUCTURE_AWARE_PRESERVATION", "BALANCED_MIX")
    highlight_decision = decide(tp10, "EXPLICIT_HIGHLIGHT", "HIGHLIGHT_EXPLICIT")
    check("TP-10 FULL_SONG_DEFAULT does NOT transition at the highlight point TP-10-C1", not decision_is_transition_at(default_decision, "TP-10-C1"), default_decision.decision_type)
    check("TP-10 BALANCED_MIX does NOT transition at the highlight point TP-10-C1", not decision_is_transition_at(balanced_decision, "TP-10-C1"), balanced_decision.decision_type)
    check("TP-10 EXPLICIT_HIGHLIGHT DOES transition at TP-10-C1 (AC4)", decision_is_transition_at(highlight_decision, "TP-10-C1"))

    print("\n=== AC2: naive/BPM-only early-exit baselines are represented and measured ===")
    check("NAIVE_EARLIEST_COMPATIBLE is a registered policy", "NAIVE_EARLIEST_COMPATIBLE" in POLICY_NAMES)
    check("BPM_KEY_ONLY_EARLY is a registered policy", "BPM_KEY_ONLY_EARLY" in POLICY_NAMES)
    with open(os.path.join(RESULTS_DIR, "metrics.json"), "r", encoding="utf-8") as f:
        metrics = json.load(f)["metrics"]
    check(
        "NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT has nonzero premature_exit_rate",
        metrics["NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT"]["premature_exit_rate"] > 0,
    )
    check(
        "BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT has nonzero premature_exit_rate",
        metrics["BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT"]["premature_exit_rate"] > 0,
    )

    print("\n=== AC3: the ~30s technically-valid-but-musically-premature case is rejected in default mode (TP-01) ===")
    tp01 = find_fixture(fixtures, "TP-01")
    tp01_decision = decide(tp01, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    check("TP-01 FULL_SONG_DEFAULT does not transition at the 30s trap TP-01-C1", not decision_is_transition_at(tp01_decision, "TP-01-C1"), tp01_decision.decision_type)
    check("TP-01 FULL_SONG_DEFAULT decision is NO_SPECIAL_TRANSITION (played through to natural outro)", tp01_decision.decision_type == "NO_SPECIAL_TRANSITION")

    print("\n=== AC5: no single elapsed-time/fraction threshold is the sole early-exit guard ===")
    with open(os.path.join(RESULTS_DIR, "sensitivity_matrix.json"), "r", encoding="utf-8") as f:
        sensitivity = json.load(f)
    all_zero = all(row["premature_exit_rate"] == 0.0 for row in sensitivity["rows"])
    check("premature_exit_rate stays 0 across every swept fraction floor (structural gate is independent of the floor)", all_zero)
    check("sensitivity sweep covers >=4 distinct thresholds (AC13)", len(sensitivity["rows"]) >= 4, f"got {len(sensitivity['rows'])}")

    print("\n=== AC6: short-track exception behavior is tested (TP-03) ===")
    tp03 = find_fixture(fixtures, "TP-03")
    tp03_decision = decide(tp03, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    check("TP-03 FULL_SONG_DEFAULT captures the short-track valid exit TP-03-C2 (fraction 0.44 < normal-length floor 0.55)", decision_is_transition_at(tp03_decision, "TP-03-C2"), tp03_decision.decision_type)

    print("\n=== AC7: long-track behavior is tested (TP-04) ===")
    tp04 = find_fixture(fixtures, "TP-04")
    tp04_structure_aware = decide(tp04, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    tp04_tail_only = decide(tp04, "TAIL_ONLY_NATURAL_EXIT_BIASED", "FULL_SONG_DEFAULT")
    check("TP-04 STRUCTURE_AWARE_PRESERVATION captures the mid-track valid exit TP-04-C2 (not overly restrictive)", decision_is_transition_at(tp04_structure_aware, "TP-04-C2"))
    check("TP-04 TAIL_ONLY_NATURAL_EXIT_BIASED misses TP-04-C2 (demonstrates over-restrictiveness contrast)", not decision_is_transition_at(tp04_tail_only, "TP-04-C2"))

    print("\n=== AC8: no-clean-outro behavior is tested (TP-05) ===")
    tp05 = find_fixture(fixtures, "TP-05")
    tp05_decision = decide(tp05, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    check("TP-05 never transitions at the technical trap TP-05-C1", not decision_is_transition_at(tp05_decision, "TP-05-C1"))
    check("TP-05 final decision is NO_SPECIAL_TRANSITION (no clean outro exists)", tp05_decision.decision_type == "NO_SPECIAL_TRANSITION")

    print("\n=== AC9: missing/low-confidence structure data causes conservative fallback (TP-09) ===")
    tp09 = find_fixture(fixtures, "TP-09")
    tp09_decision = decide(tp09, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    check("TP-09 never transitions at the unverified-confidence candidate TP-09-C1", not decision_is_transition_at(tp09_decision, "TP-09-C1"))
    check("TP-09 final decision is NO_SPECIAL_TRANSITION (conservative fallback, no fabricated certainty)", tp09_decision.decision_type == "NO_SPECIAL_TRANSITION")

    print("\n=== AC10: PLAY_THROUGH / NO_SPECIAL_TRANSITION are first-class valid results ===")
    with open(os.path.join(RESULTS_DIR, "playthrough_demo.json"), "r", encoding="utf-8") as f:
        demo = json.load(f)
    check("PLAY_THROUGH is reachable (TP-01 mid-track query)", demo["query_at_60000ms_before_outro_region"]["decision_type"] == "PLAY_THROUGH")
    check("NO_SPECIAL_TRANSITION is reachable (TP-01 end-of-track query)", demo["query_at_210000ms_natural_end"]["decision_type"] == "NO_SPECIAL_TRANSITION")

    print("\n=== AC11: queue ordering is never used as permission to exit the current track early ===")
    import copy
    tp01_poor_queue = copy.deepcopy(tp01)
    tp01_poor_queue["queue_next_track_quality"] = "POOR"
    tp01_unknown_queue = copy.deepcopy(tp01)
    tp01_unknown_queue["queue_next_track_quality"] = "UNKNOWN"
    d_excellent = decide(tp01, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    d_poor = decide(tp01_poor_queue, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    d_unknown = decide(tp01_unknown_queue, "STRUCTURE_AWARE_PRESERVATION", "FULL_SONG_DEFAULT")
    check(
        "TP-01 decision is identical regardless of queue_next_track_quality (EXCELLENT/POOR/UNKNOWN)",
        d_excellent.decision_type == d_poor.decision_type == d_unknown.decision_type
        and d_excellent.candidate_trace == d_poor.candidate_trace == d_unknown.candidate_trace,
    )
    check("PlannerDecision.queue_order_independent_of_exit_timing is always True", d_excellent.queue_order_independent_of_exit_timing is True)

    print("\n=== AC12: candidate decisions expose reason codes / traceable evidence ===")
    with open(os.path.join(RESULTS_DIR, "decision_traces.json"), "r", encoding="utf-8") as f:
        traces = json.load(f)
    all_have_trace = all(
        len(decision["candidate_trace"]) > 0
        for label, per_fixture in traces.items()
        for fixture_id, decision in per_fixture.items()
    )
    check("every (fixture, policy) decision has a non-empty candidate_trace", all_have_trace)
    all_have_reasons = all(
        (decision["decision_type"] != "PLAY_THROUGH") or len(decision["reason_codes"]) > 0
        for label, per_fixture in traces.items()
        for fixture_id, decision in per_fixture.items()
    )
    check("every non-PLAY_THROUGH decision carries reason_codes", all_have_reasons)

    print("\n=== AC18: a concrete planner-output contract is produced ===")
    sample_keys = set(tp01_decision.to_dict().keys())
    required_keys = {
        "decision_type", "current_track_exit_window_ms", "next_track_entry_window_ms",
        "preferred_transition_class_set", "confidence", "reason_codes",
        "beat_downbeat_alignment_target_ms", "permitted_tempo_pitch_envelope",
        "queue_order_independent_of_exit_timing", "candidate_trace",
    }
    check("PlannerDecision contract exposes every Task G required field", required_keys.issubset(sample_keys), f"missing={required_keys - sample_keys}")

    print(f"\n=== RESULT: {'ALL ASSERTIONS PASS' if not failures else f'{len(failures)} FAILURE(S)'} ===")
    if failures:
        for f in failures:
            print(f" - FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
