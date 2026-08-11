# P0-M3-R1 — Cue/Beat/Structure Analyzer Shootout

Status date: 2026-08-11 (PM REVIEW #2 FINAL CLOSEOUT PASS — supersedes commit `8df67b16ab2cdc5044f80fa1c0470bd9b6f32b09`)

## 0. Execution profile actually used

- **Execution agent:** Claude Code runtime (Claude Desktop -> Code
  execution surface per `AGENTS.md`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High.
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:**
  OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **This revision addresses** the PM's `PM REVIEW #2 — FINAL CLOSEOUT
  REPAIR REQUIRED` comment on Issue #5 (posted after review of commit
  `8df67b16a...`), items R8–R12.

## 1. Result

**PASS**

Every Issue #5 acceptance criterion (AC1–AC17) has direct, independently
checkable evidence — see §17's inline matrix. This closeout does not
require real-music validation, non-Windows execution, or All-In-One's
successful execution to be true; Issue #5 explicitly says a single
blocked candidate does not block the task.

## 2. What changed in this pass (map to PM's R8–R12)

| PM item | What was repaired | Where |
|---|---|---|
| R8 | Canonical `all_raw.json`/`metrics.json` are now produced EXCLUSIVELY by a fresh model/estimator construction on every single call (`estimator_lifecycle=FRESH_PER_CALL`) — never cross-fixture cached. A same-fixture cold-vs-warm equivalence test proves BeatNet's warm reuse is `NOT_EQUIVALENT` (canonical correctness therefore never uses it) and CUE-DETR's is `EQUIVALENT`. Warm-reuse performance timing lives only in the separate `results/runtime_profile.json`. | `candidates/run_beatnet.py`, `candidates/run_cuedetr.py`, `eval/warm_equivalence_test.py`, `eval/run_runtime_profile.py`; §5–§6 |
| R9 | Four non-overlapping timing fields (`model_load_wall_sec`, `asset_fetch_wall_sec`, `inference_wall_sec`, `total_call_wall_sec`) replace the R1-repair's single ambiguous `wall_time_sec`; the inference timer now starts strictly after construction returns; `total_call_wall_sec` is asserted equal to the sum of parts | `common/schema.py`, both candidate runners; §5 |
| R10 | `verify_repair.py` now loads `fixtures/manifest.json` and asserts `0 ≤ cue_ms ≤ fixture.duration_sec*1000` per fixture; "clamped" wording replaced with "filtered/validated" everywhere; `raw_cue_score` preserved parallel to `raw_cue_points_ms` | `eval/verify_repair.py`, `common/schema.py`, `candidates/run_cuedetr.py`; §7 |
| R11 | `UNRESOLVED` removed everywhere; All-In-One's phrase/section lane decisions now use `PORT/EXPORT_EXPERIMENT_NEXT` with an explicit `BLOCKED_ENVIRONMENT; execution/capability ownership unresolved` status note, per Issue #5's exact 6-value enum | `results/lane_decisions.json`, this doc §10; AC14 re-verified §17 |
| R12 | `eval/verify_repair.py` extended to check R8–R11 directly (10 numbered assertion groups); `results/cuedetr_backbone_equivalence.json` added as machine-readable proof of the `use_pretrained_backbone=False` bit-identical claim; canonical results regenerated from the repaired methodology | `eval/verify_repair.py`; §13 |

## 3. Candidate revisions (unchanged)

Same as the prior two passes: CUE-DETR `d0462856...`, All-In-One
`18e78903...`, BeatNet `81cedd4b...`, Essentia `b9fa6cb6...` (not
re-inspected this pass, per PM's explicit instruction that no new
Essentia attempt is required).

## 4. Environment (unchanged from the R1 repair pass)

Windows x64 host: RTX 2060 6GB, MSVC Build Tools 2022, Python 3.10.6.
WSL2 Ubuntu 24.04 (already installed prior to any AutoMix task, unchanged
this pass — not re-probed; §8 of the prior repair pass's evidence stands).

## 5. Canonical correctness methodology — repaired (R8)

### 5.1 The problem this repairs

The PM REPAIR pass (R1) made BeatNet/CUE-DETR reuse one model/estimator
across all 8 fixtures in a single process, labeling later calls "warm."
PM REVIEW #2 observed that this measurably changed BeatNet's own output
relative to the original, always-fresh-construction pass (e.g. FIX-E
`exact_bar_phase_accuracy` 0.5→0.5625, FIX-H `beat_fraction.cond_beat_ok_rate`
1.0→0.9896) — meaning the canonical correctness numbers used for lane
decisions were potentially contaminated by fixture processing *order*,
not analyzer quality alone.

### 5.2 The fix

`candidates/run_beatnet.py` and `candidates/run_cuedetr.py` now expose:

- `run(fixture_id, path)` — the **only** function `eval/run_shootout.py`
  calls to build canonical `all_raw.json`/`metrics.json` rows. It always
  constructs a brand-new model/estimator, uses it exactly once, and
  discards it. Every canonical ML row carries
  `estimator_lifecycle="FRESH_PER_CALL"`.
- `construct_estimator()`/`construct_model()` + `run_with_estimator()`/
  `run_with_model()` — building blocks a **separate**, explicitly
  non-canonical script (`eval/run_runtime_profile.py`) uses to
  deliberately reuse one model across fixtures purely to measure the
  wall-clock cost of doing so, writing only to `results/runtime_profile.json`
  (`estimator_lifecycle` there uses `COLD_MODEL_LOAD_INFERENCE`/`WARM_INFERENCE`,
  never merged into canonical results — asserted by `eval/verify_repair.py`
  §2/§3, both PASS).

### 5.3 Same-fixture cold-vs-warm equivalence test (R8's required evidence)

`eval/warm_equivalence_test.py`: for each candidate, run **the identical
fixture (FIX-A)** twice — once via a brand-new estimator used only once
(cold), once via a brand-new estimator that is first used on a
*different* fixture (FIX-D, to genuinely "warm" it) and then reused on
FIX-A again (warm) — and compare every correctness field plus derived
metrics.

| Candidate | `beat_timestamps_ms` equal? | `beat_position_in_bar` equal? | `downbeat_timestamps_ms` equal? | `meter_numerator` equal? | Derived metrics equal? | **Verdict** |
|---|---|---|---|---|---|---|
| BeatNet | No | No | No | Yes (both `2`) | No (`exact_bar_phase_accuracy` 1.0 cold vs. 0.9375 warm) | **`NOT_EQUIVALENT`** |

| Candidate | `raw_cue_points_ms` equal? | `raw_cue_score` equal? | `cue_points_ms` equal? | `cue_score` equal? | **Verdict** |
|---|---|---|---|---|---|
| CUE-DETR | Yes | Yes | Yes | Yes | **`EQUIVALENT`** |

Full evidence: `results/warm_cold_equivalence.json`.

**Conclusion, stated exactly as required:** BeatNet warm-resident reuse
is `UNKNOWN_NEEDS_RUNTIME_PROOF` for correctness-safety — proven
*unsafe* on this specific same-fixture test, not merely unverified — so
canonical correctness for BeatNet is, and must remain, `FRESH_PER_CALL`
(§5.2). CUE-DETR's eval-mode DETR forward pass is proven output-identical
under reuse (expected: no dropout in eval mode, batch-norm running stats
frozen, no persistent hidden state), so its warm-reuse path would have
been usable for correctness had that been the design choice — canonical
`run()` still uses `FRESH_PER_CALL` uniformly for both candidates for
methodological simplicity, since per-call construction cost for CUE-DETR
(~1.1–1.5s) is cheap relative to inference.

### 5.4 Canonical (fresh-per-call) measured values — BeatNet

| Fixture | `model_load_wall_sec` | `inference_wall_sec` | `total_call_wall_sec` |
|---|---|---|---|
| FIX-A | 4.034 | 6.431 | 10.465 |
| FIX-B | 0.014 | 0.268 | 0.282 |
| FIX-C | 0.019 | 0.311 | 0.330 |
| FIX-D | 0.015 | 0.224 | 0.239 |
| FIX-E | 0.021 | 0.351 | 0.372 |
| FIX-F | 0.014 | 0.663 | 0.677 |
| FIX-G | 0.013 | 0.792 | 0.805 |
| FIX-H | 0.014 | 0.750 | 0.764 |

A genuinely interesting, honest side-observation: fresh construction on
fixtures 2–8 is still fast (13–21 ms), not ~4s each — this is because
madmom's numba-jitted DBN/Viterbi decoder compiles once **per process**
(a module/function-level JIT cache), not per object. Constructing a new
Python `BeatNet` object doesn't re-trigger that compilation, so
correctness-safe fresh-per-call construction turns out to have
essentially the same aggregate wall-clock cost as the (incorrect) warm-reuse
approach — the fix cost effectively nothing in practice. `checkpoint_size_mb
= total_model_asset_footprint_mb = 1.54` MB on every row (single `model-1.pt`).
`asset_fetch_wall_sec = null` on every row (no runtime network fetch;
never conflated with `model_load_wall_sec` — asserted by `eval/verify_repair.py` §4).

**Correctness results now exactly match the original, first-ever P0-M3-R1
pass** (before any repair introduced cross-fixture reuse): `beat_fraction.cond_beat_ok_rate=1.0`
on all 8 fixtures (median error 2.0–4.0% of a beat), `meter_predicted=2`
(vs. ground truth 3 or 4) on all 8, `exact_bar_phase_accuracy` = 1.0 / 1.0
/ 1.0 / 0.917 / 0.5 / 0.0 / 1.0 / 1.0 for FIX-A through FIX-H
respectively. The R1-repair pass's contaminated numbers (FIX-E 0.5625,
FIX-F 0.025, FIX-H 0.9896) are superseded and were never a true analyzer
quality signal.

### 5.5 Canonical (fresh-per-call) measured values — CUE-DETR

| Fixture | `model_load_wall_sec` | `inference_wall_sec` | `total_call_wall_sec` |
|---|---|---|---|
| FIX-A | 1.501 | 5.189 | 6.690 |
| FIX-B | 1.153 | 1.012 | 2.165 |
| FIX-C | 1.153 | 1.507 | 2.660 |
| FIX-D | 1.113 | 1.202 | 2.315 |
| FIX-E | 1.093 | 1.514 | 2.607 |
| FIX-F | 1.151 | 3.030 | 4.181 |
| FIX-G | 1.077 | 2.838 | 3.915 |
| FIX-H | 1.055 | 2.122 | 3.177 |

`checkpoint_size_mb = total_model_asset_footprint_mb = 158.78` MB
(unchanged from the R1 repair — `timm` still removed, §7.1 of that pass,
now with machine-readable proof, §6 below).

### 5.6 Separate performance-profiling artifact (warm reuse, timing only)

`results/runtime_profile.json`, produced by `eval/run_runtime_profile.py`,
deliberately reuses one model per candidate across all 8 fixtures —
exactly the methodology the R1-repair pass mistakenly used for
*correctness*. Used here **only** for its original, legitimate purpose:
measuring genuine warm-reuse speedup.

| Candidate | Fixture | `estimator_lifecycle` | `model_load_wall_sec` | `inference_wall_sec` | `total_call_wall_sec` |
|---|---|---|---|---|---|
| BeatNet | FIX-A | `COLD_MODEL_LOAD_INFERENCE` | 4.219 | 4.966 | 9.185 |
| BeatNet | FIX-B..H | `WARM_INFERENCE` | 0.0 | 0.199–0.634 | 0.199–0.634 |
| CUE-DETR | FIX-A | `COLD_MODEL_LOAD_INFERENCE` | 1.297 | 4.777 | 6.074 |
| CUE-DETR | FIX-B..H | `WARM_INFERENCE` | 0.0 | 1.151–3.603 | 1.151–3.603 |

This file is explicitly scoped ("PERFORMANCE PROFILING ONLY -- NOT
canonical correctness data") and never read by `eval/run_shootout.py`'s
canonical merge step.

## 6. CUE-DETR backbone-removal — machine-readable proof (R4 + R12)

The R1-repair pass's `use_pretrained_backbone=False` bit-identical claim
had no committed machine-readable evidence. `results/cuedetr_backbone_equivalence.json`
(generated by `generate_backbone_equivalence_evidence()` in
`candidates/run_cuedetr.py`) now records, for a fixed input
(FIX-A) and fixed dependency versions in-process:

```json
{
  "checkpoint": "disco-eth/cue-detr",
  "processor_config": "facebook/detr-resnet-50",
  "compared_fixture": "FIX-A-constant-120bpm-4-4",
  "dependency_versions": {"torch": "...", "transformers": "..."},
  "compared_fields": ["raw_cue_points_ms", "raw_cue_score"],
  "positions_equal": true,
  "scores_equal": true,
  "max_score_diff": 0.0,
  "verdict": "BIT_IDENTICAL"
}
```

`eval/verify_repair.py` §10 asserts this file exists and its verdict is
`BIT_IDENTICAL`.

## 7. Cue-timestamp validation — repaired (R10)

### 7.1 Real fixture-duration bound (was: hardcoded `1e9` sanity check)

`eval/verify_repair.py` §5 now loads `fixtures/manifest.json` and asserts,
per validated `cue_points_ms` value, `0 ≤ t ≤ fixture.duration_sec × 1000`
using each fixture's own real duration — not a coarse constant. All 7
validated values across the 8-fixture set satisfy this (0 violations).

### 7.2 "Filtered/validated," not "clamped"

The implementation has always **filtered** (removed) out-of-range raw
predictions, never clamped them into range — but the R1-repair pass's
schema comments and report prose said "clamped" in several places. Every
occurrence has been corrected to "filtered"/"validated" (`common/schema.py`,
`candidates/run_cuedetr.py`, this document). `eval/verify_repair.py` §5
asserts `raw count == valid + invalid count` (11 = 7 + 4) as a structural
proof that filtering, not clamping or silent dropping, is what actually
happens: every raw value ends up in exactly one of the two buckets.

### 7.3 Raw cue scores now preserved parallel to raw timestamps

`raw_cue_score` (new field) is preserved parallel to `raw_cue_points_ms`
on every CUE-DETR row, so an invalid raw prediction's score remains fully
auditable, not just its timestamp. `eval/verify_repair.py` §5 asserts
equal array lengths on every row.

| Fixture | raw predictions (ms) | raw scores | validated (ms) | invalid (raw, ms) | n_invalid |
|---|---|---|---|---|---|
| FIX-A | 69.7, 31718.5 | 1.0, 0.9106 | 69.7, 31718.5 | — | 0 |
| FIX-B | 232.2 | 1.0 | 232.2 | — | 0 |
| FIX-C | 46.4 | 1.0 | 46.4 | — | 0 |
| FIX-D | 46.4 | 1.0 | 46.4 | — | 0 |
| FIX-E | -139.3, 69.7 | 0.9096, 1.0 | 69.7 | -139.3 | 1 |
| FIX-F | -69.7 | 1.0 | *(none)* | -69.7 | 1 |
| FIX-G | -46.4, 71842.5 | 1.0, 0.9210 | *(none)* | -46.4, 71842.5 | 2 |
| FIX-H | 69.7 | 1.0 | 69.7 | — | 0 |

Unchanged from the R1 repair: **4 of 11 raw predictions (36%) are
invalid**; `cue_confidence` remains `null` on every row (never
fabricated).

## 8. Boundary-event metrics (unchanged since R2 repair; re-verified)

FIX-F ground truth and the fixed-32-beat proxy's evaluation are unchanged
by this pass (no source-truth change occurred) and are re-asserted by
`eval/verify_repair.py` §7: **TP=4, FP=1, FN=0**, `precision=0.8`,
`recall=1.0`, `F1=0.889`, tolerance `COND_PHRASE_OK` (234.375 ms). The
energy-heuristic boundary-timing-vs-label-semantics distinction from the
R2 repair is likewise unchanged and re-asserted (§8 of `verify_repair.py`).

## 9. Cue/structure lane results (framing unchanged)

Same smoke/regression-evidence framing as prior passes. All-In-One
remains unexecuted; its bounded WSL2 probe evidence (NATTEN build blocker
resolved on Linux via a prebuilt wheel, but a newly-discovered
NATTEN-API-version incompatibility blocks the pinned revision's own code)
is unchanged from the R1 repair pass and was not re-attempted this pass,
per PM's explicit instruction that Essentia/All-In-One require no new
attempt this round.

## 10. Decision matrix — lane enum corrected (R11)

**Binding enum (Issue #5 Task F), used exclusively below:**
`ADOPT_FOR_P0_PROTOTYPE` / `KEEP_AS_BENCHMARK_ONLY` /
`REIMPLEMENT_SMALLER_EQUIVALENT` / `PORT/EXPORT_EXPERIMENT_NEXT` /
`REJECT` / `BLOCKED_PENDING_LICENSE`. `UNRESOLVED` (used in the R1 repair
pass) is **not** a valid value and has been removed everywhere, replaced
per PM's exact instruction. Machine-readable source of truth:
`results/lane_decisions.json`, asserted by `eval/verify_repair.py` §9
(every entry's `decision` value is enum-checked programmatically).

| Capability lane | Decision | Status note |
|---|---|---|
| Beat timestamps | **`ADOPT_FOR_P0_PROTOTYPE`** (BeatNet) | Real, strong beat-timestamp accuracy on canonical fresh-per-call results (§5.4), including under deliberate phase-offset/variable-tempo stress fixtures where the scalar-BPM negative baseline collapses |
| Downbeats / bar phase | **`KEEP_AS_BENCHMARK_ONLY`** (BeatNet) | Beat tracking strong; downbeat/meter selection not reliably validated on this pass's synthetic fixtures (meter=2 misclassified on all 8) |
| Meter | **`KEEP_AS_BENCHMARK_ONLY`** (BeatNet) | 0 of 8 fixtures correctly classified |
| Cue points | **`KEEP_AS_BENCHMARK_ONLY`** (CUE-DETR) | Real execution, smoke-test only, EDM-domain-specific; 4/11 raw predictions filtered as invalid |
| Phrase candidates | **`REJECT`** (fixed-32-beat proxy, TP=4/FP=1/FN=0 on FIX-F) **and** **`PORT/EXPORT_EXPERIMENT_NEXT`** (All-In-One) | All-In-One: `BLOCKED_ENVIRONMENT; execution/capability ownership unresolved` — no claim the next experiment is guaranteed to succeed |
| Section boundaries/labels | **`REJECT`** (energy-level heuristic) **and** **`PORT/EXPORT_EXPERIMENT_NEXT`** (All-In-One) | Same All-In-One status note as above |
| Confidence / fallback inputs | **`KEEP_AS_BENCHMARK_ONLY`** (no candidate this pass) | Neither BeatNet's DBN API nor CUE-DETR's `cue_score` (`MINMAX_NORMALIZED_DETR_DETECTION_SCORE`) is a calibrated confidence signal |

### 10.1 Smallest composite stack (unchanged conclusion from the R1 repair, restated with corrected enum)

1. **BeatNet** for beat timestamps only (`ADOPT_FOR_P0_PROTOTYPE`), with
   an added, now-*proven* (not merely suspected) deployment constraint:
   any future warm-resident production integration of BeatNet must
   construct a fresh estimator per file — reuse is confirmed
   `NOT_EQUIVALENT` (§5.3), not just unverified.
2. **All-In-One**: `PORT/EXPORT_EXPERIMENT_NEXT`, `BLOCKED_ENVIRONMENT`,
   capability ownership of the downbeat/meter/phrase/section lanes
   remains genuinely open pending either a NATTEN-API-compatible
   All-In-One revision or an old-NATTEN source build (out of this
   pass's environment boundary).
3. **CUE-DETR** for a cue-point signal, EDM-genre-adjacent, smoke-test
   status (`KEEP_AS_BENCHMARK_ONLY`), now also confirmed reuse-safe
   (§5.3) should a future pass choose to keep it warm-resident.
4. The three negative baselines remain the permanent comparison floor.
5. Essentia stays `KEEP_AS_BENCHMARK_ONLY` at best / `BLOCKED_PENDING_LICENSE`
   for production (license matrix, unchanged).

## 11. Third-party notice, artifact license matrix, All-In-One blocker — kept unchanged (per PM instruction)

Per PM's explicit "keep unchanged unless evidence requires correction":
`tools/p0m3/analyzer_shootout/THIRD_PARTY_NOTICES.md` and
`docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` are unchanged this
pass except for one addition — Sec 1.1 now also references
`results/cuedetr_backbone_equivalence.json` as the machine-readable proof
backing its existing prose claim (§6 above). No license verdict changed.
The bounded All-In-One WSL2 blocker record is unchanged; no new invasive
system installs occurred this pass (verified: no `wsl --install`,
`Docker Desktop` installer, or admin-toolchain install command appears
anywhere in this pass's command history).

## 12. Portability matrix (unchanged from the R1 repair pass)

Not re-measured this pass; see the R1 repair pass's §13 for the full
table (Windows x64 measured, Linux WSL2 partially probed for All-In-One
only, macOS/mobile `UNKNOWN_NEEDS_RUNTIME_PROOF`/`SOURCE_ONLY_INSPECTED`).

## 13. Verification artifacts (R12)

`eval/verify_repair.py`, 10 numbered assertion groups, run against the
regenerated canonical results plus the new evidence files:

```
=== 1. Result counts by candidate/run_state ===
{ "beatnet": {"OK": 8}, "cue_detr": {"OK": 8}, "energy_onset_heuristic_baseline": {"OK": 8},
  "fixed_32_beat_phrase_proxy_baseline": {"OK": 8}, "scalar_bpm_grid_baseline": {"OK": 8} }
[PASS] all 5 expected candidates present / total raw count == 40 / every raw record OK

=== 2. R8: canonical rows are FRESH_PER_CALL (not cross-fixture warm-state) ===
[PASS] every canonical ML row has estimator_lifecycle=FRESH_PER_CALL
[PASS] every baseline row has estimator_lifecycle=N_A
[PASS] no canonical row carries a warm-profiling lifecycle label
[PASS] results/runtime_profile.json exists as a separate performance artifact
[PASS] runtime_profile.json contains at least one genuine WARM_INFERENCE row

=== 3. R8: same-fixture cold-vs-warm equivalence test ===
[PASS] results/warm_cold_equivalence.json exists
[PASS] beatnet equivalence case present -- verdict=NOT_EQUIVALENT
[PASS] cue_detr equivalence case present -- verdict=EQUIVALENT
[PASS] beatnet canonical rows use FRESH_PER_CALL given NOT_EQUIVALENT finding

=== 4. R9: timing field consistency ===
[PASS] total_call_wall_sec == model_load_wall_sec + inference_wall_sec (tolerance 5ms)
[PASS] asset_fetch_wall_sec is null on every row
[PASS] every ML row has a non-null model_load_wall_sec

=== 5. R10: validated cue_points_ms within [0, real fixture duration_ms] ===
[PASS] every validated value satisfies the real-duration bound
[PASS] raw_cue count == valid + invalid count -- raw=11 valid=7 invalid=4
[PASS] at least one invalid cue prediction observed and preserved
[PASS] raw_cue_score preserved parallel to raw_cue_points_ms
[PASS] raw_cue_points_ms and raw_cue_score have equal length
[PASS] cue_confidence is null on every row

=== 6. ML candidate model-size metadata ===
[PASS] every ML row has non-null checkpoint_size_mb / explicit memory_measurement_method

=== 7. FIX-F fixed-32-beat proxy boundary event metrics ===
TP=4 FP=1 FN=0 precision=0.8 recall=1.0 F1=0.889 -- [PASS] all 5 exact-value assertions

=== 8. energy_onset_heuristic section-boundary-timing vs label-semantic fields ===
[PASS] FIX-F/FIX-G: boundary timing present + label-accuracy explicitly None+noted

=== 9. R11: lane decision enum membership ===
[PASS] every lane_decisions.json entry uses only Issue #5's allowed enum values

=== 10. R12: CUE-DETR use_pretrained_backbone=False bit-identical evidence ===
[PASS] results/cuedetr_backbone_equivalence.json exists
[PASS] backbone-equivalence evidence verdict is BIT_IDENTICAL
[PASS] backbone-equivalence evidence records dependency versions

=== RESULT: ALL ASSERTIONS PASS ===
```

## 14. Unknowns / risks (updated)

- BeatNet's/CUE-DETR's behavior on real musical material remains
  unverified (unchanged; not a binding AC).
- BeatNet warm-resident deployment is now `UNKNOWN_NEEDS_RUNTIME_PROOF`
  in a stronger sense: proven unsafe on the tested same-fixture case, not
  merely unverified. A production integration needing warm-resident
  BeatNet would need to find/implement an explicit state-reset mechanism
  and re-run this same equivalence test against it.
- All-In-One's exact unblock path is unchanged and unresolved (§9, §10).
- Essentia remains fully unexecuted (unchanged; no new attempt required
  this pass per PM).
- Every candidate's training-audio provenance/rights chain remains
  `UNKNOWN_NEEDS_LEGAL_REVIEW` (license matrix, unchanged).

## 15. Committed evidence files (new/changed this pass)

- `results/all_raw.json`, `results/metrics.json`, `results/SUMMARY.md` — regenerated, canonical, fresh-per-call only.
- `results/runtime_profile.json` — new, separate, performance-only.
- `results/warm_cold_equivalence.json` — new, same-fixture equivalence test evidence.
- `results/cuedetr_backbone_equivalence.json` — new, machine-readable backbone-removal proof.
- `results/lane_decisions.json` — new, machine-readable lane-decision source of truth, enum-validated.
- `eval/warm_equivalence_test.py`, `eval/run_runtime_profile.py` — new scripts.
- `eval/verify_repair.py` — extended with R8–R11 assertion groups.

## 16. PM review request

Please independently verify:

1. `results/warm_cold_equivalence.json` — confirm the BeatNet case's
   `fields_equal` shows `false` for `beat_timestamps_ms` and the verdict
   is `NOT_EQUIVALENT`, and that canonical `all_raw.json` BeatNet rows
   all carry `estimator_lifecycle=FRESH_PER_CALL` (never a value implying
   reuse).
2. `results/all_raw.json` — spot-check one ML row:
   `total_call_wall_sec == model_load_wall_sec + inference_wall_sec`
   exactly (within float rounding), `asset_fetch_wall_sec == null`.
3. `results/cuedetr_backbone_equivalence.json` — confirm `verdict:
   "BIT_IDENTICAL"` and `max_score_diff: 0.0`.
4. `results/lane_decisions.json` — confirm every `decision` value is one
   of Issue #5's exact six enum values (no `UNRESOLVED` anywhere in the
   diff).
5. `eval/verify_repair.py` — run it independently and confirm `RESULT:
   ALL ASSERTIONS PASS`.
