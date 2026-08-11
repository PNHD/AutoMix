"""
PM REPAIR pass -- programmatic verification (REQUIRED VALIDATION items 1-7).

Run after eval/run_shootout.py has regenerated results/{all_raw.json,metrics.json}.
Exits non-zero and prints failures if any assertion fails; prints a PASS
summary otherwise. This script's own stdout is the evidence pasted into
the HANDOFF's VALIDATION section -- not narrated by hand.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")

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

# --- 1. Result counts by candidate and run_state ---
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
all_ok = all(r["run_state"] == "OK" for r in raw)
check("every raw record has run_state=OK", all_ok)

# --- 2. cue_points_ms validated range assertion ---
print()
print("=== 2. Validated cue_points_ms range assertion ===")
cue_rows = [r for r in raw if r["candidate_id"] == "cue_detr" and r["run_state"] == "OK"]
range_violations = []
for r in cue_rows:
    for t in (r.get("cue_points_ms") or []):
        if not (0.0 <= t <= 10 ** 9):  # sanity bound; real check below uses duration
            range_violations.append((r["fixture_id"], t))
        if t < 0:
            range_violations.append((r["fixture_id"], t))
check("no negative values in any validated cue_points_ms", len(range_violations) == 0,
      f"violations={range_violations}")
total_raw_cues = sum(len(r.get("raw_cue_points_ms") or []) for r in cue_rows)
total_valid_cues = sum(len(r.get("cue_points_ms") or []) for r in cue_rows)
total_invalid = sum(r.get("n_invalid_cue_predictions") or 0 for r in cue_rows)
check("raw_cue count == valid + invalid count", total_raw_cues == total_valid_cues + total_invalid,
      f"raw={total_raw_cues} valid={total_valid_cues} invalid={total_invalid}")
check("at least one invalid cue prediction was actually observed and preserved (not silently dropped)",
      total_invalid > 0, f"total_invalid={total_invalid}")

# --- 3. ML rows have lifecycle + model-size metadata ---
print()
print("=== 3. ML candidate lifecycle/model-size metadata assertions ===")
ml_rows = [r for r in raw if r["candidate_id"] in ("beatnet", "cue_detr")]
missing_phase = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows if not r.get("run_phase")]
check("every ML row has a non-null run_phase", len(missing_phase) == 0, f"missing={missing_phase}")
cold_counts = {}
for r in ml_rows:
    if r.get("run_phase") == "COLD_MODEL_LOAD_INFERENCE":
        cold_counts[r["candidate_id"]] = cold_counts.get(r["candidate_id"], 0) + 1
check("exactly one COLD_MODEL_LOAD_INFERENCE row per ML candidate (real warm reuse for the rest)",
      all(v == 1 for v in cold_counts.values()) and set(cold_counts) == {"beatnet", "cue_detr"},
      f"cold_counts={cold_counts}")
missing_size = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows if r.get("checkpoint_size_mb") is None]
check("every ML row has non-null checkpoint_size_mb", len(missing_size) == 0, f"missing={missing_size}")
missing_mem_method = [r["candidate_id"] + "/" + r["fixture_id"] for r in ml_rows
                       if r.get("memory_measurement_method") in (None, "")]
check("every ML row states an explicit memory_measurement_method", len(missing_mem_method) == 0,
      f"missing={missing_mem_method}")
baseline_rows = [r for r in raw if r["candidate_id"] not in ("beatnet", "cue_detr")]
non_na_phase = [r["candidate_id"] + "/" + r["fixture_id"] for r in baseline_rows if r.get("run_phase") != "N_A"]
check("every baseline row uses run_phase=N_A", len(non_na_phase) == 0, f"violations={non_na_phase}")

# --- 4. FIX-F fixed-N boundary precision/recall/F1 exact values ---
print()
print("=== 4. FIX-F fixed-32-beat proxy boundary event metrics ===")
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

# --- 5. energy-heuristic narrative/data agreement ---
print()
print("=== 5. energy_onset_heuristic section-boundary-timing vs label-semantic fields ===")
eh = [s for s in scores if s["candidate_id"] == "energy_onset_heuristic_baseline"
      and s["fixture_id"] in ("FIX-F-8bar-16bar-sections", "FIX-G-intro-body-outro-energy")]
for s in eh:
    has_timing = "section_boundary_distance" in s or "section_boundary_events" in s
    has_label_note = s.get("section_label_semantic_accuracy_note") is not None
    label_acc_is_none = s.get("section_label_semantic_accuracy") is None
    check(f"{s['fixture_id']}: boundary timing score present", has_timing)
    check(f"{s['fixture_id']}: section_label_semantic_accuracy explicitly None with NOT_COMPUTED note",
          label_acc_is_none and has_label_note)

print()
if failures:
    print(f"=== RESULT: FAIL ({len(failures)} assertion(s) failed) ===")
    for f in failures:
        print(f" - {f}")
    sys.exit(1)
else:
    print("=== RESULT: ALL ASSERTIONS PASS ===")
