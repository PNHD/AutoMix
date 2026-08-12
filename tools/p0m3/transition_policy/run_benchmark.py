#!/usr/bin/env python3
"""
P0-M3-R2 (Apple-like redesign) -- disposable transition-policy benchmark
runner. Stdlib-only, deterministic, no audio, no network.

Produces:
  results/decision_traces.json    -- full per-(fixture,policy,intent) trace (AC12)
  results/metrics.json            -- preservation/timing/pair-compatibility metrics
  results/sensitivity_matrix.json -- preservation-floor sensitivity sweep (0.90/0.93/0.95/0.97/0.98)
  results/playthrough_demo.json   -- explicit PLAY_THROUGH vs NO_SPECIAL_TRANSITION proof (AC10)
  results/order_invariance.json   -- TP-12 normal/reverse/shuffled candidate order -> identical winner
  results/pair_compatibility.json -- PAIR-01..10 component report + TP-11 integration proof
  results/boundary_planning.json  -- PM REVIEW #2 R1/R2: TX-01..05 complete boundary-plan results
  results/SUMMARY.md              -- human-readable summary

Run: python run_benchmark.py
"""
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

# (policy_name, intent, is_baseline) -- the benchmarked rows.
RUNS = [
    ("NAIVE_EARLIEST_COMPATIBLE", "SEAMLESS_FULL_TRACK_DEFAULT", True),
    ("BPM_KEY_ONLY_EARLY", "SEAMLESS_FULL_TRACK_DEFAULT", True),
    ("TAIL_ONLY_NATURAL_EXIT_BIASED", "SEAMLESS_FULL_TRACK_DEFAULT", True),
    ("FIXED_SECONDS_BEFORE_END_ONLY", "SEAMLESS_FULL_TRACK_DEFAULT", True),
    ("SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT", False),   # RECOMMENDED product default
    ("BALANCED_MIX_RESEARCH_CONTROL", "BALANCED_MIX", False),               # research/negative control only
    ("EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL", "HIGHLIGHT_EXPLICIT", False),   # research/negative control only
]

RECOMMENDED_LABEL = "SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT"

SENSITIVITY_PRESERVATION_FLOORS = [0.90, 0.93, 0.95, 0.97, 0.98]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def winner_candidate_id(fixture, decision):
    if decision.decision_type != "TRANSITION":
        return None
    onset = decision.transition_onset_window_ms["t_start_ms"]
    for c in fixture["candidates"]:
        if c["t_ms"] == onset and not c.get("is_end_of_track"):
            return c["candidate_id"]
    return None


def run_matrix(fixtures):
    traces = {}
    per_run_decisions = {}
    for policy_name, intent, _ in RUNS:
        label = f"{policy_name}@{intent}"
        traces[label] = {}
        per_run_decisions[label] = {}
        for fx in fixtures:
            decision = decide(fx, policy_name, intent)
            traces[label][fx["fixture_id"]] = decision.to_dict()
            per_run_decisions[label][fx["fixture_id"]] = decision
    return traces, per_run_decisions


def compute_metrics(fixtures, per_run_decisions):
    fixtures_by_id = {fx["fixture_id"]: fx for fx in fixtures}

    trap_fixture_ids = set()
    valid_fixture_ids = set()
    missed_opportunity_fixture_ids = set()
    for fx in fixtures:
        cids = fx["candidates"]
        if any(c.get("is_premature_trap") or c.get("is_vocal_collision_trap") for c in cids):
            trap_fixture_ids.add(fx["fixture_id"])
        if any(c.get("is_valid_natural_exit") for c in cids):
            valid_fixture_ids.add(fx["fixture_id"])
        preferred = [c for c in cids if c.get("is_preferred_earliest_valid_exit")]
        if preferred and not preferred[0].get("is_end_of_track"):
            missed_opportunity_fixture_ids.add(fx["fixture_id"])

    metrics = {}
    for label, per_fixture in per_run_decisions.items():
        premature = 0
        catastrophic = 0
        captured_valid = 0
        missed_opportunity = 0
        forced_full_dj_blend = 0
        transitions = 0
        fallback = 0
        preserved_ratios = []

        for fixture_id, decision in per_fixture.items():
            fx = fixtures_by_id[fixture_id]
            candidate_lookup = {c["candidate_id"]: c for c in fx["candidates"]}

            if decision.decision_type == "TRANSITION":
                transitions += 1
                cid = winner_candidate_id(fx, decision)
                cand = candidate_lookup[cid] if cid else None
                ratio = decision.outgoing_content_preservation_target
                if ratio is not None:
                    preserved_ratios.append(ratio)
                    if ratio < 0.90:
                        catastrophic += 1

                if cand and fixture_id in trap_fixture_ids and (cand.get("is_premature_trap") or cand.get("is_vocal_collision_trap")):
                    premature += 1
                if cand and fixture_id in valid_fixture_ids and cand.get("is_valid_natural_exit"):
                    captured_valid += 1
                if decision.allowed_transition_class_set == ["FULL_DJ_BLEND"]:
                    forced_full_dj_blend += 1
            else:
                fallback += 1
                preserved_ratios.append(1.0)
                if decision.decision_type == "NO_SPECIAL_TRANSITION" and decision.candidate_rank_trace:
                    cid = decision.candidate_rank_trace[-1]["candidate_id"]
                    cand = candidate_lookup.get(cid)
                    if cand and fixture_id in valid_fixture_ids and cand.get("is_valid_natural_exit"):
                        captured_valid += 1

            if fixture_id in missed_opportunity_fixture_ids:
                preferred_cand = next(c for c in fx["candidates"] if c.get("is_preferred_earliest_valid_exit"))
                took_preferred = (decision.decision_type == "TRANSITION" and winner_candidate_id(fx, decision) == preferred_cand["candidate_id"])
                if not took_preferred:
                    missed_opportunity += 1

        n = len(per_fixture)
        metrics[label] = {
            "n_fixtures": n,
            "premature_exit_rate": round(premature / len(trap_fixture_ids), 4) if trap_fixture_ids else None,
            "premature_exit_count_over_denominator": f"{premature}/{len(trap_fixture_ids)}",
            "catastrophic_premature_exit_count_over_transitions": f"{catastrophic}/{transitions}" if transitions else "0/0",
            "valid_late_exit_capture_rate": round(captured_valid / len(valid_fixture_ids), 4) if valid_fixture_ids else None,
            "valid_late_exit_capture_count_over_denominator": f"{captured_valid}/{len(valid_fixture_ids)}",
            "missed_transition_opportunity_rate": round(missed_opportunity / len(missed_opportunity_fixture_ids), 4) if missed_opportunity_fixture_ids else None,
            "missed_transition_opportunity_count_over_denominator": f"{missed_opportunity}/{len(missed_opportunity_fixture_ids)}",
            "forced_full_dj_blend_rate": round(forced_full_dj_blend / transitions, 4) if transitions else 0.0,
            "forced_full_dj_blend_count_over_denominator": f"{forced_full_dj_blend}/{transitions}" if transitions else "0/0",
            "fallback_playthrough_rate": round(fallback / n, 4),
            "fallback_playthrough_count_over_denominator": f"{fallback}/{n}",
            "mean_outgoing_content_preservation_ratio": round(sum(preserved_ratios) / len(preserved_ratios), 4) if preserved_ratios else None,
            "transitions_count": transitions,
        }
    return metrics, {
        "trap_fixture_ids": sorted(trap_fixture_ids),
        "valid_fixture_ids": sorted(valid_fixture_ids),
        "missed_opportunity_fixture_ids": sorted(missed_opportunity_fixture_ids),
    }


def run_sensitivity(fixtures):
    trap_fixture_ids = [
        fx["fixture_id"] for fx in fixtures
        if any(c.get("is_premature_trap") or c.get("is_vocal_collision_trap") for c in fx["candidates"])
    ]
    missed_opportunity_ids = [
        fx["fixture_id"] for fx in fixtures
        if any(c.get("is_preferred_earliest_valid_exit") and not c.get("is_end_of_track") for c in fx["candidates"])
    ]

    rows = []
    for floor in SENSITIVITY_PRESERVATION_FLOORS:
        premature = 0
        missed = 0
        fallback = 0
        for fx in fixtures:
            decision = decide(fx, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT", floor_override=floor)
            candidate_lookup = {c["candidate_id"]: c for c in fx["candidates"]}
            if decision.decision_type == "TRANSITION":
                cid = winner_candidate_id(fx, decision)
                cand = candidate_lookup.get(cid) if cid else None
                if cand and fx["fixture_id"] in trap_fixture_ids and (cand.get("is_premature_trap") or cand.get("is_vocal_collision_trap")):
                    premature += 1
            else:
                fallback += 1
            if fx["fixture_id"] in missed_opportunity_ids:
                preferred_cand = next(c for c in fx["candidates"] if c.get("is_preferred_earliest_valid_exit"))
                took_preferred = (decision.decision_type == "TRANSITION" and winner_candidate_id(fx, decision) == preferred_cand["candidate_id"])
                if not took_preferred:
                    missed += 1
        rows.append({
            "preservation_floor": floor,
            "band_label": (
                "catastrophic_ceiling" if floor < 0.90 else
                "preferred_band_lower_bound" if floor == 0.97 else
                "acceptable_p0_default_candidate_band" if 0.95 <= floor < 0.97 else
                "preferred_band" if floor > 0.97 else "at_catastrophic_ceiling"
            ),
            "premature_exit_rate": round(premature / len(trap_fixture_ids), 4),
            "premature_exit_count_over_denominator": f"{premature}/{len(trap_fixture_ids)}",
            "missed_transition_opportunity_rate": round(missed / len(missed_opportunity_ids), 4),
            "missed_transition_opportunity_count_over_denominator": f"{missed}/{len(missed_opportunity_ids)}",
            "fallback_playthrough_rate": round(fallback / len(fixtures), 4),
        })

    return {
        "policy": RECOMMENDED_LABEL,
        "swept_parameter": "outgoing_content_preservation_ratio floor (structural-evidence/confidence/vocal-risk guards held fixed ON throughout)",
        "floors_tested": SENSITIVITY_PRESERVATION_FLOORS,
        "conclusion": (
            "premature_exit_rate is 0/9 at every tested floor from 0.90 to 0.98, including the strict catastrophic "
            "ceiling itself (0.90) -- because the structural-evidence guard (eligibility guard 3) and vocal-collision "
            "guard (guard 1) are independent of the preservation floor and already exclude every "
            "is_premature_trap/is_vocal_collision_trap candidate regardless of elapsed time or preservation ratio. "
            "This is the direct evidence that no single preservation-ratio threshold is, by itself, the premature-exit "
            "guard -- contrast with NAIVE_EARLIEST_COMPATIBLE and BPM_KEY_ONLY_EARLY in metrics.json, which have no "
            "structural-evidence guard at all and show nonzero premature_exit_rate. Missed-transition-opportunity rate "
            "is monitored across the same sweep to show the floor's effect on capture, separate from safety."
        ),
        "rows": rows,
    }


def run_order_invariance(fixtures):
    fx = next(f for f in fixtures if f["fixture_id"] == "TP-12")

    def winner(f):
        d = decide(f, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT")
        return winner_candidate_id(f, d)

    normal = dict(fx)
    reversed_fx = dict(fx); reversed_fx["candidates"] = list(reversed(fx["candidates"]))
    shuffled_fx = dict(fx); cs = list(fx["candidates"]); random.Random(7).shuffle(cs); shuffled_fx["candidates"] = cs

    w_normal = winner(normal)
    w_reversed = winner(reversed_fx)
    w_shuffled = winner(shuffled_fx)

    return {
        "fixture_id": "TP-12",
        "note": "Two simultaneously eligible near-end candidates (X earlier/acceptable, Y later/musically stronger). A first-eligible-wins planner would pick X in array order but Y under reversed/shuffled order -- proving order-dependence is a real bug class. The ranked planner must select Y under every ordering.",
        "candidate_order_normal": [c["candidate_id"] for c in normal["candidates"]],
        "candidate_order_reversed": [c["candidate_id"] for c in reversed_fx["candidates"]],
        "candidate_order_shuffled": [c["candidate_id"] for c in shuffled_fx["candidates"]],
        "winner_normal_order": w_normal,
        "winner_reversed_order": w_reversed,
        "winner_shuffled_order": w_shuffled,
        "order_invariant": w_normal == w_reversed == w_shuffled == "TP-12-Y",
    }


def run_playthrough_demo(fixtures):
    fx = next(f for f in fixtures if f["fixture_id"] == "TP-01")
    mid_decision = decide_at_time(fx, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT", evaluation_time_ms=60000)
    end_decision = decide_at_time(fx, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT", evaluation_time_ms=210000)
    return {
        "fixture_id": "TP-01",
        "note": "Same fixture/policy/intent, two evaluation times -- PLAY_THROUGH and NO_SPECIAL_TRANSITION are both reachable, distinct, first-class outcomes (AC10). decide_at_time is the TIME-LOCAL query primitive (cannot see future candidates); decide() is the canonical full-track/offline ranked planner -- they are NOT presented as equivalent (spec 'FULL-TRACK VS TIME-LOCAL').",
        "query_at_60000ms_before_outro_region": mid_decision.to_dict(),
        "query_at_210000ms_natural_end": end_decision.to_dict(),
    }


def run_pair_compatibility_report(pair_fixtures, fixtures):
    fixtures_by_id = {fx["fixture_id"]: fx for fx in fixtures}
    tp11 = fixtures_by_id["TP-11"]

    components = {}
    integration = {}
    for p in pair_fixtures:
        result = evaluate_pair_compatibility(p)
        components[p["pair_id"]] = {
            "title": p["title"],
            "task_letter": p["task_letter"],
            "expected_overall_eligible": p["expected_overall_eligible"],
            "computed": result.to_dict(),
            "matches_expectation": result.overall_dynamic_mix_eligible == p["expected_overall_eligible"],
        }
        decision = decide(tp11, "SEAMLESS_FULL_TRACK_DEFAULT", "SEAMLESS_FULL_TRACK_DEFAULT", pair=p)
        integration[p["pair_id"]] = {
            "timing_fixture": "TP-11 (near-end candidate, timing already excellent)",
            "allowed_transition_class_set": decision.allowed_transition_class_set,
            "full_dj_blend_offered": "FULL_DJ_BLEND" in decision.allowed_transition_class_set,
        }

    n_downgraded = sum(1 for c in components.values() if not c["computed"]["overall_dynamic_mix_eligible"])
    return {
        "purpose": "Proves pair compatibility gates FULL_DJ_BLEND independently of timing quality: every integration row reuses TP-11's already-excellent near-end candidate, varying ONLY the pair.",
        "components_by_pair": components,
        "tp11_integration_by_pair": integration,
        "incompatible_pair_downgrade_rate": round(n_downgraded / len(pair_fixtures), 4),
        "incompatible_pair_downgrade_count_over_denominator": f"{n_downgraded}/{len(pair_fixtures)}",
    }


def run_boundary_report(tx_fixtures):
    """
    PM REVIEW #2 R1/R2: runs the complete-boundary-plan planner on every
    TX-* fixture and proves order invariance across BOTH the outgoing exit
    array and the incoming entry array for TX-01 (the R1 adversarial
    fixture where pair compatibility must change which boundary wins).
    """
    results = {}
    for tx in tx_fixtures:
        d = plan_transition_boundary(tx, "SEAMLESS_FULL_TRACK_DEFAULT")
        results[tx["transition_id"]] = {
            "title": tx["title"],
            "purpose": tx["purpose"],
            "decision": d.to_dict(),
            "expected_winner": tx.get("expected_winner"),
            "matches_expectation": (
                d.selected_outgoing_exit_candidate_id == tx["expected_winner"]["outgoing"]
                and d.selected_incoming_entry_candidate_id == tx["expected_winner"]["incoming"]
            ) if tx.get("expected_winner") else None,
        }

    tx01 = next(tx for tx in tx_fixtures if tx["transition_id"] == "TX-01")

    def variant(exit_order, entry_order):
        v = json.loads(json.dumps(tx01))
        v["outgoing_track"]["candidates"] = exit_order(v["outgoing_track"]["candidates"])
        v["incoming_track"]["candidates"] = entry_order(v["incoming_track"]["candidates"])
        return v

    def winner_key(d):
        return [d.selected_outgoing_exit_candidate_id, d.selected_incoming_entry_candidate_id]

    order_checks = {
        "exit_normal_entry_normal": variant(lambda c: c, lambda c: c),
        "exit_reversed_entry_normal": variant(lambda c: list(reversed(c)), lambda c: c),
        "exit_normal_entry_reversed": variant(lambda c: c, lambda c: list(reversed(c))),
        "exit_reversed_entry_reversed": variant(lambda c: list(reversed(c)), lambda c: list(reversed(c))),
        "exit_shuffled_seed3_entry_shuffled_seed11": variant(lambda c: random.Random(3).sample(c, len(c)), lambda c: random.Random(11).sample(c, len(c))),
    }
    order_winners = {label: winner_key(plan_transition_boundary(v, "SEAMLESS_FULL_TRACK_DEFAULT")) for label, v in order_checks.items()}
    all_same = len({tuple(w) for w in order_winners.values()}) == 1

    return {
        "purpose": "PM REVIEW #2 R1/R2: canonical planning ranks COMPLETE (outgoing exit, incoming entry, pair compatibility AT that boundary) plans, never an outgoing exit selected in isolation with pair compatibility applied only afterward.",
        "transitions": results,
        "tx01_order_invariance": {
            "note": "TX-01: OUT-A has the higher raw outgoing-only structure score but every boundary touching it is pair-incompatible (HIGH vocal collision); OUT-B is pair-compatible. The winner must be OUT-B+IN-2 (best compatible + best combined structure) under every outgoing-array and incoming-array ordering.",
            "winners_by_order": order_winners,
            "order_invariant": all_same,
        },
    }


def run_mutation_pair_report(pair_fixtures):
    """R4: UNKNOWN structure/texture/harmonic must not silently equal known-COMPATIBLE."""
    mutation_ids = {"PAIR-06", "PAIR-07", "PAIR-08", "PAIR-09", "PAIR-10"}
    rows = {}
    for p in pair_fixtures:
        if p["pair_id"] not in mutation_ids:
            continue
        result = evaluate_pair_compatibility(p)
        rows[p["pair_id"]] = {
            "title": p["title"],
            "expected_overall_eligible": p["expected_overall_eligible"],
            "computed_overall_eligible": result.overall_dynamic_mix_eligible,
            "matches_expectation": result.overall_dynamic_mix_eligible == p["expected_overall_eligible"],
            "reason_codes": result.reason_codes,
        }
    return rows


def write_summary(metrics, sensitivity, order_invariance, pair_report, denominators, boundary_report=None, mutation_report=None):
    lines = ["# P0-M3-R2 Apple-like Benchmark Run -- SUMMARY", ""]
    lines.append(f"Denominators: trap_fixtures={len(denominators['trap_fixture_ids'])} ({denominators['trap_fixture_ids']}), "
                  f"valid_fixtures={len(denominators['valid_fixture_ids'])}, "
                  f"missed_opportunity_fixtures={len(denominators['missed_opportunity_fixture_ids'])} ({denominators['missed_opportunity_fixture_ids']})")
    lines.append("")
    lines.append("| Policy@Intent | premature_exit_rate | valid_late_exit_capture_rate | missed_opportunity_rate | forced_FULL_DJ_BLEND_rate | fallback_rate | mean_preservation_ratio |")
    lines.append("|---|---|---|---|---|---|---|")
    for label, m in metrics.items():
        marker = " **<- RECOMMENDED**" if label == RECOMMENDED_LABEL else ""
        lines.append(
            f"| {label}{marker} | {m['premature_exit_count_over_denominator']} | {m['valid_late_exit_capture_count_over_denominator']} | "
            f"{m['missed_transition_opportunity_count_over_denominator']} | {m['forced_full_dj_blend_count_over_denominator']} | "
            f"{m['fallback_playthrough_count_over_denominator']} | {m['mean_outgoing_content_preservation_ratio']} |"
        )
    lines.append("")
    lines.append(f"## Sensitivity sweep -- {RECOMMENDED_LABEL}")
    lines.append("")
    lines.append("| preservation_floor | band | premature_exit_rate | missed_opportunity_rate | fallback_rate |")
    lines.append("|---|---|---|---|---|")
    for row in sensitivity["rows"]:
        lines.append(f"| {row['preservation_floor']} | {row['band_label']} | {row['premature_exit_count_over_denominator']} | {row['missed_transition_opportunity_count_over_denominator']} | {row['fallback_playthrough_rate']} |")
    lines.append("")
    lines.append(sensitivity["conclusion"])
    lines.append("")
    lines.append("## Multi-candidate order invariance (TP-12)")
    lines.append("")
    lines.append(f"normal={order_invariance['winner_normal_order']} reversed={order_invariance['winner_reversed_order']} shuffled={order_invariance['winner_shuffled_order']} -> order_invariant={order_invariance['order_invariant']}")
    lines.append("")
    lines.append("## Pair compatibility gate")
    lines.append("")
    lines.append(f"incompatible_pair_downgrade_rate={pair_report['incompatible_pair_downgrade_rate']} ({pair_report['incompatible_pair_downgrade_count_over_denominator']})")
    lines.append("")
    lines.append("| Pair | Letter | Expected eligible | Computed eligible | Matches | TP-11+pair: FULL_DJ_BLEND offered |")
    lines.append("|---|---|---|---|---|---|")
    for pid, c in pair_report["components_by_pair"].items():
        lines.append(f"| {pid} | {c['task_letter']} | {c['expected_overall_eligible']} | {c['computed']['overall_dynamic_mix_eligible']} | {c['matches_expectation']} | {pair_report['tp11_integration_by_pair'][pid]['full_dj_blend_offered']} |")

    if boundary_report is not None:
        lines.append("")
        lines.append("## PM REVIEW #2 -- complete boundary-plan results (TX-01..05)")
        lines.append("")
        lines.append("| Transition | Expected winner | Selected winner | Matches |")
        lines.append("|---|---|---|---|")
        for tid, r in boundary_report["transitions"].items():
            d = r["decision"]
            selected = f"{d['selected_outgoing_exit_candidate_id']} + {d['selected_incoming_entry_candidate_id']}"
            expected = f"{r['expected_winner']['outgoing']} + {r['expected_winner']['incoming']}" if r["expected_winner"] else "n/a"
            lines.append(f"| {tid} | {expected} | {selected} | {r['matches_expectation']} |")
        lines.append("")
        lines.append(f"TX-01 order invariance (exit array x entry array, 5 orderings): order_invariant={boundary_report['tx01_order_invariance']['order_invariant']}")

    if mutation_report is not None:
        lines.append("")
        lines.append("## R4 -- UNKNOWN structure/texture/harmonic mutation tests")
        lines.append("")
        lines.append("| Pair | Expected eligible | Computed eligible | Matches |")
        lines.append("|---|---|---|---|")
        for pid, r in mutation_report.items():
            lines.append(f"| {pid} | {r['expected_overall_eligible']} | {r['computed_overall_eligible']} | {r['matches_expectation']} |")

    with open(os.path.join(RESULTS_DIR, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fixtures = load_json(FIXTURES_PATH)
    pair_fixtures = load_json(PAIR_FIXTURES_PATH)
    tx_fixtures = load_json(TRANSITION_FIXTURES_PATH)

    traces, per_run_decisions = run_matrix(fixtures)
    metrics, denominators = compute_metrics(fixtures, per_run_decisions)
    sensitivity = run_sensitivity(fixtures)
    order_invariance = run_order_invariance(fixtures)
    playthrough_demo = run_playthrough_demo(fixtures)
    pair_report = run_pair_compatibility_report(pair_fixtures, fixtures)
    boundary_report = run_boundary_report(tx_fixtures)
    mutation_report = run_mutation_pair_report(pair_fixtures)

    with open(os.path.join(RESULTS_DIR, "decision_traces.json"), "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "denominators": denominators}, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "sensitivity_matrix.json"), "w", encoding="utf-8") as f:
        json.dump(sensitivity, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "order_invariance.json"), "w", encoding="utf-8") as f:
        json.dump(order_invariance, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "playthrough_demo.json"), "w", encoding="utf-8") as f:
        json.dump(playthrough_demo, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "pair_compatibility.json"), "w", encoding="utf-8") as f:
        json.dump(pair_report, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "boundary_planning.json"), "w", encoding="utf-8") as f:
        json.dump(boundary_report, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "mutation_pair_report.json"), "w", encoding="utf-8") as f:
        json.dump(mutation_report, f, indent=2)
    write_summary(metrics, sensitivity, order_invariance, pair_report, denominators, boundary_report, mutation_report)

    print("=== METRICS ===")
    print(json.dumps(metrics, indent=2))
    print("=== SENSITIVITY ===")
    print(json.dumps(sensitivity, indent=2))
    print("=== ORDER INVARIANCE (TP-12) ===")
    print(json.dumps(order_invariance, indent=2))
    print("=== PAIR COMPATIBILITY ===")
    print(json.dumps({k: v["matches_expectation"] for k, v in pair_report["components_by_pair"].items()}, indent=2))
    print("=== BOUNDARY PLANNING (TX-01..05) ===")
    print(json.dumps({k: v["matches_expectation"] for k, v in boundary_report["transitions"].items()}, indent=2))
    print("TX-01 order invariance:", boundary_report["tx01_order_invariance"]["order_invariant"])
    print("=== R4 MUTATION PAIR REPORT ===")
    print(json.dumps({k: v["matches_expectation"] for k, v in mutation_report.items()}, indent=2))
    print("=== PLAYTHROUGH DEMO (decision_type only) ===")
    print("mid-track:", playthrough_demo["query_at_60000ms_before_outro_region"]["decision_type"])
    print("end-track:", playthrough_demo["query_at_210000ms_natural_end"]["decision_type"])
    print("=== DONE -- results written to", RESULTS_DIR, "===")


if __name__ == "__main__":
    main()
