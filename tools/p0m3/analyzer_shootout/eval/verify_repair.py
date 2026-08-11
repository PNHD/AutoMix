"""
PM REPAIR + PM REVIEW #2 -- programmatic verification (all REQUIRED
VALIDATION items across both review rounds).

Run after eval/run_shootout.py has regenerated canonical
results/{all_raw.json,metrics.json}, and after eval/warm_equivalence_test.py
has produced results/warm_cold_equivalence.json. Exits non-zero and prints
failures if any assertion fails; prints a PASS summary otherwise. This
script's own stdout is the evidence pasted into the HANDOFF's VALIDATION
section -- not narrated by hand.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")

# Issue #5 Task F's exact, binding lane-decision enum. No other value is valid.
ALLOWED_LANE_DECISIONS = {
    "ADOPT_FOR_P0_PROTOTYPE",
    "KEEP_AS_BENCHMARK_ONLY",
    "REIMPLEMENT_SMALLER_EQUIVALENT",
    "PORT/EXPORT_EXPERIMENT_NEXT",
    "REJECT",
    "BLOCKED_PENDING_LICENSE",
}

failures = []


def check(label: str, cond: bool, detail: str = ""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail else ""))
    if not cond:
        failures.append(label)


with open(os.path.join(RESULTS, "all_raw.json")) as f:
    raw = json.load(f)
with open(os.path.join(RESULTS, "metrics.json")) as f:
    scores = json.load(f)
with open(os.path.join(ROOT, "fixtures", "manifest.json")) as f:
    manifest = json.load(f)
duration_ms_by_fixture = {e["fixture_id"]: e["ground_truth"]["duration_sec"] * 1000.0 for e in manifest["fixtures"]}

# =====================================================================
# 1. Result counts by candidate and run_state
# =====================================================================
by_candidate = {}
for r in raw:
    by_candidate.setdefault(r["candidate_id"], {}).setdefault(r["run_state"], 0)
    by_candidate[r["candidate_id"]][r["run_state"]] += 1
print("=== 1. Result counts by candidate/run_state ===")
print(json.dumps(by_candidate, indent=2))
expected_candidates = {
    "scalar_bpm_grid_baseline", "fixed_32_beat_phrase_proxy_baseline",
    "energy_onset_heuristic_baseline", "beatnet", "cue_detr",
}
check("all 5 expected candidates present", expected_candidates.issubset(set(by_candidate.keys())),
      f"present={sorted(by_candidate.keys())}")
check("total raw count == 40", len(raw) == 40, f"actual={len(raw)}")
check("every raw record has run_state=OK", all(r["run_state"] == "OK" for r in raw))

# =====================================================================
# 2. R8 -- canonical rows are fixture-independent (fresh-per-call), not
#    cross-file warm-state contaminated
# =====================================================================
print()
print("=== 2. R8: canonical rows are FRESH_PER_CALL (not cross-fixture warm-state) ===")
ml_rows = [r for r in raw if r["candidate_id"] in ("beatnet", "cue_detr")]
non_fresh = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows if r.get("estimator_lifecycle") != "FRESH_PER_CALL"]
check("every canonical ML row has estimator_lifecycle=FRESH_PER_CALL", len(non_fresh) == 0,
      f"violations={non_fresh}")
baseline_rows = [r for r in raw if r["candidate_id"] not in ("beatnet", "cue_detr")]
non_na = [r["candidate_id"] + "/" + r["fixture_id"] for r in baseline_rows if r.get("estimator_lifecycle") != "N_A"]
check("every baseline row has estimator_lifecycle=N_A", len(non_na) == 0, f"violations={non_na}")

# The separate runtime_profile.json (if present) must carry the
# COLD_MODEL_LOAD_INFERENCE/WARM_INFERENCE labels instead, and must never
# be the source of all_raw.json/metrics.json (checked by construction:
# all_raw.json rows are all FRESH_PER_CALL/N_A, never those two labels).
contaminating_labels = {"COLD_MODEL_LOAD_INFERENCE", "WARM_INFERENCE"}
leaked = [r["candidate_id"] + "/" + r["fixture_id"] for r in raw
          if r.get("estimator_lifecycle") in contaminating_labels]
check("no canonical row carries a warm-profiling lifecycle label (COLD_MODEL_LOAD_INFERENCE/WARM_INFERENCE)",
      len(leaked) == 0, f"leaked={leaked}")

runtime_profile_path = os.path.join(RESULTS, "runtime_profile.json")
check("results/runtime_profile.json exists as a separate performance artifact",
      os.path.exists(runtime_profile_path))
if os.path.exists(runtime_profile_path):
    with open(runtime_profile_path) as f:
        profile = json.load(f)
    profile_rows = profile.get("rows", [])
    has_warm = any(r.get("estimator_lifecycle") == "WARM_INFERENCE" for r in profile_rows)
    check("runtime_profile.json contains at least one genuine WARM_INFERENCE row (real reuse measured)",
          has_warm)

# =====================================================================
# 3. R8 -- same-fixture cold-vs-warm equivalence test has explicit PASS/FAIL
# =====================================================================
print()
print("=== 3. R8: same-fixture cold-vs-warm equivalence test ===")
equiv_path = os.path.join(RESULTS, "warm_cold_equivalence.json")
check("results/warm_cold_equivalence.json exists", os.path.exists(equiv_path))
if os.path.exists(equiv_path):
    with open(equiv_path) as f:
        equiv = json.load(f)
    equiv_by_candidate = {c["candidate"]: c for c in equiv}
    check("beatnet equivalence case present with explicit verdict",
          "beatnet" in equiv_by_candidate and equiv_by_candidate["beatnet"]["verdict"] in ("EQUIVALENT", "NOT_EQUIVALENT"),
          f"verdict={equiv_by_candidate.get('beatnet', {}).get('verdict')}")
    check("cue_detr equivalence case present with explicit verdict",
          "cue_detr" in equiv_by_candidate and equiv_by_candidate["cue_detr"]["verdict"] in ("EQUIVALENT", "NOT_EQUIVALENT"),
          f"verdict={equiv_by_candidate.get('cue_detr', {}).get('verdict')}")
    beatnet_verdict = equiv_by_candidate.get("beatnet", {}).get("verdict")
    print(f"    beatnet same-fixture warm-reuse verdict: {beatnet_verdict} "
          f"(canonical correctness therefore MUST be FRESH_PER_CALL, checked in Sec 2)")
    cuedetr_verdict = equiv_by_candidate.get("cue_detr", {}).get("verdict")
    print(f"    cue_detr same-fixture warm-reuse verdict: {cuedetr_verdict}")
    # If BeatNet were ever found EQUIVALENT, warm-resident deployment could
    # be considered safe; since this pass found NOT_EQUIVALENT, canonical
    # correctness must never depend on a reused estimator. Assert the
    # methodology matches whatever the equivalence result actually says.
    if beatnet_verdict == "NOT_EQUIVALENT":
        check("beatnet canonical rows use FRESH_PER_CALL given NOT_EQUIVALENT warm-reuse finding",
              len([r for r in ml_rows if r["candidate_id"] == "beatnet"
                   and r.get("estimator_lifecycle") != "FRESH_PER_CALL"]) == 0)

# =====================================================================
# 4. R9 -- timing fields are non-overlapping and consistent
# =====================================================================
print()
print("=== 4. R9: timing field consistency (model_load + inference == total_call) ===")
timing_violations = []
for r in ml_rows:
    if r["run_state"] != "OK":
        continue
    load = r.get("model_load_wall_sec") or 0.0
    infer = r.get("inference_wall_sec")
    total = r.get("total_call_wall_sec")
    if infer is None or total is None:
        timing_violations.append((r["candidate_id"], r["fixture_id"], "missing inference/total field"))
        continue
    if abs((load + infer) - total) > 0.005:
        timing_violations.append((r["candidate_id"], r["fixture_id"], f"load={load} infer={infer} total={total}"))
check("total_call_wall_sec == model_load_wall_sec + inference_wall_sec on every ML row (tolerance 5ms)",
      len(timing_violations) == 0, f"violations={timing_violations}")
mislabeled_asset_fetch = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows
                           if r.get("asset_fetch_wall_sec") is not None]
check("asset_fetch_wall_sec is null on every row (no runtime network fetch separately measured; "
      "never conflated with model construction)", len(mislabeled_asset_fetch) == 0,
      f"non-null={mislabeled_asset_fetch}")
missing_load = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows if r.get("model_load_wall_sec") is None]
check("every ML row has a non-null model_load_wall_sec", len(missing_load) == 0, f"missing={missing_load}")

# =====================================================================
# 5. R10 -- cue validation uses REAL fixture duration
# =====================================================================
print()
print("=== 5. R10: validated cue_points_ms within [0, real fixture duration_ms] ===")
cue_rows = [r for r in raw if r["candidate_id"] == "cue_detr" and r["run_state"] == "OK"]
range_violations = []
for r in cue_rows:
    dur_ms = duration_ms_by_fixture.get(r["fixture_id"])
    for t in (r.get("cue_points_ms") or []):
        if dur_ms is None or not (0.0 <= t <= dur_ms):
            range_violations.append((r["fixture_id"], t, dur_ms))
check("every validated cue_points_ms value satisfies 0<=t<=fixture.duration_sec*1000",
      len(range_violations) == 0, f"violations={range_violations}")

total_raw_cues = sum(len(r.get("raw_cue_points_ms") or []) for r in cue_rows)
total_valid_cues = sum(len(r.get("cue_points_ms") or []) for r in cue_rows)
total_invalid = sum(r.get("n_invalid_cue_predictions") or 0 for r in cue_rows)
check("raw_cue count == valid + invalid count (filtered, not clamped -- no value both kept and dropped)",
      total_raw_cues == total_valid_cues + total_invalid,
      f"raw={total_raw_cues} valid={total_valid_cues} invalid={total_invalid}")
check("at least one invalid cue prediction was actually observed and preserved (not silently dropped)",
      total_invalid > 0, f"total_invalid={total_invalid}")
missing_raw_score = [r["fixture_id"] for r in cue_rows if r.get("raw_cue_score") is None]
check("raw_cue_score is preserved parallel to raw_cue_points_ms on every cue_detr row",
      len(missing_raw_score) == 0, f"missing={missing_raw_score}")
for r in cue_rows:
    n_raw_pts = len(r.get("raw_cue_points_ms") or [])
    n_raw_scores = len(r.get("raw_cue_score") or [])
    if n_raw_pts != n_raw_scores:
        failures.append(f"raw_cue_points_ms/raw_cue_score length mismatch on {r['fixture_id']}")
check("raw_cue_points_ms and raw_cue_score have equal length on every row (genuinely parallel arrays)",
      all(len(r.get("raw_cue_points_ms") or []) == len(r.get("raw_cue_score") or []) for r in cue_rows))
fabricated_confidence = [r["fixture_id"] for r in cue_rows if r.get("cue_confidence") is not None]
check("cue_confidence is null on every row (no calibrated confidence fabricated)",
      len(fabricated_confidence) == 0, f"non-null={fabricated_confidence}")

# =====================================================================
# 6. ML lifecycle/model-size metadata (carried from PM REPAIR R1)
# =====================================================================
print()
print("=== 6. ML candidate model-size metadata assertions ===")
missing_size = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows if r.get("checkpoint_size_mb") is None]
check("every ML row has non-null checkpoint_size_mb", len(missing_size) == 0, f"missing={missing_size}")
missing_mem_method = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows
                       if r.get("memory_measurement_method") in (None, "")]
check("every ML row states an explicit memory_measurement_method", len(missing_mem_method) == 0,
      f"missing={missing_mem_method}")

# =====================================================================
# 7. FIX-F fixed-N boundary precision/recall/F1 exact values (unchanged
#    since source truth -- the fixture/proxy code -- has not changed)
# =====================================================================
print()
print("=== 7. FIX-F fixed-32-beat proxy boundary event metrics (must remain TP=4/FP=1/FN=0) ===")
fixf = [s for s in scores if s["fixture_id"] == "FIX-F-8bar-16bar-sections"
        and s["candidate_id"] == "fixed_32_beat_phrase_proxy_baseline"]
if fixf:
    ev = fixf[0].get("phrase_boundary_events", {})
    print(json.dumps(ev, indent=2))
    check("FIX-F fixed-32 proxy: n_gt==4", ev.get("n_gt") == 4, f"actual={ev.get('n_gt')}")
    check("FIX-F fixed-32 proxy: n_pred==5", ev.get("n_pred") == 5, f"actual={ev.get('n_pred')}")
    check("FIX-F fixed-32 proxy: TP==4", ev.get("tp") == 4, f"actual={ev.get('tp')}")
    check("FIX-F fixed-32 proxy: FP==1", ev.get("fp") == 1, f"actual={ev.get('fp')}")
    check("FIX-F fixed-32 proxy: FN==0", ev.get("fn") == 0, f"actual={ev.get('fn')}")
else:
    check("FIX-F fixed-32 proxy score record exists", False)

# =====================================================================
# 8. energy-heuristic narrative/data agreement (carried from PM REPAIR R2)
# =====================================================================
print()
print("=== 8. energy_onset_heuristic section-boundary-timing vs label-semantic fields ===")
eh = [s for s in scores if s["candidate_id"] == "energy_onset_heuristic_baseline"
      and s["fixture_id"] in ("FIX-F-8bar-16bar-sections", "FIX-G-intro-body-outro-energy")]
for s in eh:
    has_timing = "section_boundary_distance" in s or "section_boundary_events" in s
    has_label_note = s.get("section_label_semantic_accuracy_note") is not None
    label_acc_is_none = s.get("section_label_semantic_accuracy") is None
    check(f"{s['fixture_id']}: boundary timing score present", has_timing)
    check(f"{s['fixture_id']}: section_label_semantic_accuracy explicitly None with NOT_COMPUTED note",
          label_acc_is_none and has_label_note)

# =====================================================================
# 9. R11 -- every lane decision belongs to Issue #5's exact enum
# =====================================================================
print()
print("=== 9. R11: lane decision enum membership ===")
lane_decisions_path = os.path.join(ROOT, "results", "lane_decisions.json")
if os.path.exists(lane_decisions_path):
    with open(lane_decisions_path) as f:
        lane_decisions = json.load(f)
    bad = []
    for lane, entries in lane_decisions.items():
        if lane.startswith("_"):
            continue
        for e in entries:
            if e["decision"] not in ALLOWED_LANE_DECISIONS:
                bad.append((lane, e["decision"]))
    check("every lane_decisions.json entry uses only Issue #5's allowed enum values", len(bad) == 0,
          f"invalid={bad}")
    print(json.dumps(lane_decisions, indent=2))
else:
    check("results/lane_decisions.json exists (machine-readable lane decision source of truth)", False)

# =====================================================================
# 10. R12 -- CUE-DETR backbone-removal machine evidence exists
# =====================================================================
print()
print("=== 10. R12: CUE-DETR use_pretrained_backbone=False bit-identical evidence ===")
backbone_ev_path = os.path.join(RESULTS, "cuedetr_backbone_equivalence.json")
check("results/cuedetr_backbone_equivalence.json exists", os.path.exists(backbone_ev_path))
if os.path.exists(backbone_ev_path):
    with open(backbone_ev_path) as f:
        bev = json.load(f)
    check("backbone-equivalence evidence verdict is BIT_IDENTICAL", bev.get("verdict") == "BIT_IDENTICAL",
          f"verdict={bev.get('verdict')} max_score_diff={bev.get('max_score_diff')}")
    check("backbone-equivalence evidence records dependency versions", bool(bev.get("dependency_versions")))

print()
if failures:
    print(f"=== RESULT: FAIL ({len(failures)} assertion(s) failed) ===")
    for f in failures:
        print(f" - {f}")
    sys.exit(1)
else:
    print("=== RESULT: ALL ASSERTIONS PASS ===")
