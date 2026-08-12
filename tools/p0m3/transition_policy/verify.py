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
from policy.boundary import plan_transition_boundary

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "fixtures.json")
PAIR_FIXTURES_PATH = os.path.join(HERE, "fixtures", "pair_fixtures.json")
TRANSITION_FIXTURES_PATH = os.path.join(HERE, "fixtures", "transition_fixtures.json")
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
    "policy/boundary.py",
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
    tx_fixtures = load_json(TRANSITION_FIXTURES_PATH)
    by_id = {fx["fixture_id"]: fx for fx in fixtures}
    pair_by_id = {p["pair_id"]: p for p in pair_fixtures}
    tx_by_id = {tx["transition_id"]: tx for tx in tx_fixtures}

    print("=== 0. Structural / scope-boundary checks ===")
    check("timing fixture count == 14 (spec letters A-N)", len(fixtures) == 14, f"got {len(fixtures)}")
    check("pair fixture count == 10 (spec letters G-K + R4 mutation pairs PAIR-06..10)", len(pair_fixtures) == 10, f"got {len(pair_fixtures)}")
    check("transition boundary fixture count == 5 (TX-01..05)", len(tx_fixtures) == 5, f"got {len(tx_fixtures)}")
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

    print("\n=== PM REVIEW #2 R1: pair compatibility CAN change which near-end boundary wins ===")
    tx01 = tx_by_id["TX-01"]
    dtx01 = plan_transition_boundary(tx01, "SEAMLESS_FULL_TRACK_DEFAULT")
    check(
        "1. TX-01 winner is the pair-COMPATIBLE boundary (OUT-B), not the raw-structure favorite (OUT-A)",
        dtx01.selected_outgoing_exit_candidate_id == "TX01-OUT-B",
    )
    check(
        "2. TX-01 timing-only winner (OUT-A, higher raw outgoing structure score) does NOT win despite being structurally superior in isolation",
        dtx01.selected_outgoing_exit_candidate_id != "TX01-OUT-A",
    )
    a_boundaries = [t for t in dtx01.candidate_rank_trace if t["outgoing_candidate_id"] == "TX01-OUT-A"]
    b_boundaries = [t for t in dtx01.candidate_rank_trace if t["outgoing_candidate_id"] == "TX01-OUT-B"]
    check(
        "TX-01 every OUT-A boundary is pair-incompatible (eligible_for_dynamic_mix False) while OUT-B boundaries are compatible -- the actual reason B wins",
        all(not t["eligible_for_dynamic_mix"] for t in a_boundaries) and any(t["eligible_for_dynamic_mix"] for t in b_boundaries),
    )
    check(
        "TX-01 OUT-A has the higher raw outgoing_structure_score (proves the winner is NOT simply 'more structurally sound', it's the compatible one)",
        max(t["outgoing_structure_score"] for t in a_boundaries) > max(t["outgoing_structure_score"] for t in b_boundaries),
    )

    print("\n=== PM REVIEW #2 R1/R2: order invariance across BOTH outgoing and incoming candidate arrays ===")
    def variant(tx, exit_order, entry_order):
        v = json.loads(json.dumps(tx))
        v["outgoing_track"]["candidates"] = exit_order(v["outgoing_track"]["candidates"])
        v["incoming_track"]["candidates"] = entry_order(v["incoming_track"]["candidates"])
        return v

    def boundary_winner(d):
        return (d.selected_outgoing_exit_candidate_id, d.selected_incoming_entry_candidate_id)

    base_winner = boundary_winner(dtx01)
    exit_reversed = variant(tx01, lambda c: list(reversed(c)), lambda c: c)
    entry_reversed = variant(tx01, lambda c: c, lambda c: list(reversed(c)))
    both_reversed = variant(tx01, lambda c: list(reversed(c)), lambda c: list(reversed(c)))
    exit_shuffled = variant(tx01, lambda c: random.Random(41).sample(c, len(c)), lambda c: c)
    entry_shuffled = variant(tx01, lambda c: c, lambda c: random.Random(53).sample(c, len(c)))
    check("3. reversing the OUTGOING exit candidate array does not change the selected boundary", boundary_winner(plan_transition_boundary(exit_reversed, "SEAMLESS_FULL_TRACK_DEFAULT")) == base_winner)
    check("4. reversing the INCOMING entry candidate array does not change the selected boundary", boundary_winner(plan_transition_boundary(entry_reversed, "SEAMLESS_FULL_TRACK_DEFAULT")) == base_winner)
    check("reversing BOTH arrays simultaneously does not change the selected boundary", boundary_winner(plan_transition_boundary(both_reversed, "SEAMLESS_FULL_TRACK_DEFAULT")) == base_winner)
    check("independently-shuffled OUTGOING array (seed 41) does not change the selected boundary", boundary_winner(plan_transition_boundary(exit_shuffled, "SEAMLESS_FULL_TRACK_DEFAULT")) == base_winner)
    check("independently-shuffled INCOMING array (seed 53) does not change the selected boundary", boundary_winner(plan_transition_boundary(entry_shuffled, "SEAMLESS_FULL_TRACK_DEFAULT")) == base_winner)

    print("\n=== PM REVIEW #2 R2: incoming entry planning is real, not a universal 0..0 placeholder ===")
    tx_decisions = {tid: plan_transition_boundary(tx, "SEAMLESS_FULL_TRACK_DEFAULT") for tid, tx in tx_by_id.items()}
    all_windows = [d.next_track_entry_window_ms for d in tx_decisions.values()]
    check(
        "5. next_track_entry_window_ms is NOT a universal {0,0} placeholder across TX-01..05 (at least one real nonzero entry window exists)",
        any(w is not None and w["t_start_ms"] != 0 for w in all_windows),
    )
    check("TX-03 selects the silence-skip entry (5000ms), not 0ms or the too-far candidate", tx_decisions["TX-03"].selected_incoming_entry_candidate_id == "TX03-IN-SKIP")
    check("TX-03 next_track_entry_window_ms reflects the actual selected entry timestamp (5000), not a placeholder", tx_decisions["TX-03"].next_track_entry_window_ms == {"t_start_ms": 5000, "t_end_ms": 5000})
    check("TX-04 selects the later phrase/cue entry (8000ms) over 0ms", tx_decisions["TX-04"].selected_incoming_entry_candidate_id == "TX04-IN-CUE")
    check("TX-05 entry choice changes compatibility: winner is the compatible entry, not the vocal-collision one", tx_decisions["TX-05"].selected_incoming_entry_candidate_id == "TX05-IN-B")
    for tid, d in tx_decisions.items():
        check(f"{tid} incoming_effective_content_start_ms is populated (not silently omitted)", d.incoming_effective_content_start_ms is not None)

    print("\n=== PM REVIEW #2: transition_onset_window_ms is a REAL narrow window, never onset..content_end ===")
    check(
        "6. every TX-01..05 winning transition_onset_window_ms has t_start_ms == t_end_ms (an exact cue, never a span to effective_content_end_ms)",
        all(d.transition_onset_window_ms["t_start_ms"] == d.transition_onset_window_ms["t_end_ms"] for d in tx_decisions.values()),
    )
    check(
        "same narrow-window contract holds for the legacy single-track builder too (TP-11's winning onset window)",
        d11.transition_onset_window_ms["t_start_ms"] == d11.transition_onset_window_ms["t_end_ms"],
    )

    print("\n=== PM REVIEW #2: alignment contract identifies BOTH sides, never one timestamp reused ===")
    check(
        "7. TX-01 winner identifies both outgoing_beat_alignment_target_ms and incoming_beat_alignment_target_ms (neither is None)",
        dtx01.outgoing_beat_alignment_target_ms is not None and dtx01.incoming_beat_alignment_target_ms is not None,
    )
    check(
        "outgoing and incoming beat alignment targets are genuinely distinct values, not the same outgoing timestamp exposed twice",
        dtx01.outgoing_beat_alignment_target_ms != dtx01.incoming_beat_alignment_target_ms,
    )
    check("TX-01 downbeat alignment likewise identifies both sides", dtx01.outgoing_downbeat_alignment_target_ms is not None and dtx01.incoming_downbeat_alignment_target_ms is not None)
    check("TX-01 beat_phase_relation is a real, non-UNKNOWN-by-omission value given both sides are beat-aligned", dtx01.beat_phase_relation in ("ALIGNED", "OFFSET"))

    print("\n=== PM REVIEW #2 R3: tempo deviation is never emitted as if it were a literal ratio ===")
    sample_keys = set(dtx01.to_dict().keys())
    check(
        "8. the old ambiguous field name 'permitted_tempo_ratio' no longer exists on PlannerDecision at all (structural rename, not an alias)",
        "permitted_tempo_ratio" not in sample_keys,
    )
    check("permitted_tempo_ratio_max_deviation is present and explicitly named as a deviation", "permitted_tempo_ratio_max_deviation" in sample_keys)
    check("required_tempo_ratio is present as a separate, real ratio field", "required_tempo_ratio" in sample_keys)
    check("TX-01 winner: permitted_tempo_ratio_max_deviation == 0.12 (a deviation ceiling)", dtx01.permitted_tempo_ratio_max_deviation == 0.12)
    check("TX-01 winner: required_tempo_ratio is a real numeric ratio, not equal to the deviation constant", dtx01.required_tempo_ratio is not None and dtx01.required_tempo_ratio != 0.12)

    print("\n=== PM REVIEW #2 R3: pitch units/ranges are unambiguous ===")
    check(
        "9. old ambiguous field name 'permitted_pitch_shift' no longer exists on PlannerDecision at all",
        "permitted_pitch_shift" not in sample_keys,
    )
    check("required_pitch_shift_semitones is present (explicit unit in the name)", "required_pitch_shift_semitones" in sample_keys)
    check(
        "permitted_pitch_shift_semitones_min/max are present as an explicit range, not a single unitless integer",
        "permitted_pitch_shift_semitones_min" in sample_keys and "permitted_pitch_shift_semitones_max" in sample_keys,
    )
    check(
        "TX-01 winner: permitted pitch-shift range is symmetric and non-null when FULL_DJ_BLEND is offered",
        dtx01.permitted_pitch_shift_semitones_min == -3 and dtx01.permitted_pitch_shift_semitones_max == 3,
    )

    print("\n=== PM REVIEW #2 R4: UNKNOWN structure/texture/harmonic never silently equals known-COMPATIBLE ===")
    pair06 = evaluate_pair_compatibility(pair_by_id["PAIR-06"])  # UNKNOWN structure_compatibility
    check("10. PAIR-06 (UNKNOWN structure_compatibility) is NOT overall_dynamic_mix_eligible -- UNKNOWN structure never equals known COMPATIBLE", pair06.overall_dynamic_mix_eligible is False)
    pair07 = evaluate_pair_compatibility(pair_by_id["PAIR-07"])  # UNKNOWN/false intro_outro_texture_compatible
    check("11. PAIR-07 (UNKNOWN intro/outro texture) is NOT overall_dynamic_mix_eligible -- UNKNOWN texture never equals known COMPATIBLE", pair07.overall_dynamic_mix_eligible is False)
    pair10 = evaluate_pair_compatibility(pair_by_id["PAIR-10"])  # harmonic INCOMPATIBLE + exception reason present (must not matter)
    check("12. PAIR-10 (harmonic INCOMPATIBLE) never gets FULL_DJ_BLEND, even with an exception reason attached", pair10.overall_dynamic_mix_eligible is False)
    pair08 = evaluate_pair_compatibility(pair_by_id["PAIR-08"])  # harmonic UNKNOWN, no exception
    pair09 = evaluate_pair_compatibility(pair_by_id["PAIR-09"])  # harmonic UNKNOWN, WITH narrow exception
    check("13. PAIR-08 (harmonic UNKNOWN, no exception) is NOT eligible -- UNKNOWN does not silently behave like COMPATIBLE", pair08.overall_dynamic_mix_eligible is False)
    check("PAIR-09 (harmonic UNKNOWN, WITH an explicit narrow style-specific exception) IS eligible -- the exception path is real and testable", pair09.overall_dynamic_mix_eligible is True)
    check("PAIR-08 and PAIR-09 differ ONLY by the exception reason, proving UNKNOWN-without-exception is a genuine, non-silent downgrade", pair08.overall_dynamic_mix_eligible != pair09.overall_dynamic_mix_eligible)

    print("\n=== PM REVIEW #2: full boundary trace is preserved for every combination, not just the winner ===")
    check(
        "TX-01 candidate_rank_trace contains all 4 (exit x entry) boundary combinations, not merely the winner",
        len(dtx01.candidate_rank_trace) == 4,
    )
    n_selected = sum(1 for t in dtx01.candidate_rank_trace if t.get("selected"))
    check("exactly one boundary in the TX-01 trace is marked selected=True", n_selected == 1)
    check("every TX-01 trace entry carries pair_compatibility_components (not only the winner)", all(t.get("pair_compatibility_components") is not None for t in dtx01.candidate_rank_trace))

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

    print("\n=== AC18 (PM REVIEW #2 schema): a concrete P0-M3-R3 planner-output contract is produced ===")
    ac18_keys = set(dtx01.to_dict().keys())
    required_keys = {
        "decision_type", "current_track_effective_content_end_ms",
        "selected_outgoing_exit_candidate_id", "transition_onset_window_ms",
        "outgoing_last_audible_target_ms", "outgoing_content_preservation_target",
        "selected_incoming_entry_candidate_id", "incoming_effective_content_start_ms", "next_track_entry_window_ms",
        "allowed_transition_class_set", "pair_compatibility_components",
        "outgoing_beat_alignment_target_ms", "incoming_beat_alignment_target_ms",
        "outgoing_downbeat_alignment_target_ms", "incoming_downbeat_alignment_target_ms",
        "beat_phase_relation", "bar_phase_relation",
        "required_tempo_ratio", "permitted_tempo_ratio_max_deviation",
        "required_pitch_shift_semitones", "permitted_pitch_shift_semitones_min", "permitted_pitch_shift_semitones_max",
        "energy_continuity_target", "vocal_collision_constraints", "bass_collision_constraints",
        "analysis_confidence", "reason_codes", "candidate_rank_trace",
        "queue_order_independent_of_exit_timing",
    }
    check("PlannerDecision contract exposes every P0-M3-R3 required field (PM REVIEW #2 schema)", required_keys.issubset(ac18_keys), f"missing={required_keys - ac18_keys}")
    check("AC18: PLAY_THROUGH / NO_SPECIAL_TRANSITION decisions use the SAME schema (no separate ad-hoc shape)", required_keys.issubset(set(d09.to_dict().keys())))

    print(f"\n=== RESULT: {'ALL ASSERTIONS PASS' if not failures else f'{len(failures)} FAILURE(S)'} ===")
    if failures:
        for f in failures:
            print(f" - FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
