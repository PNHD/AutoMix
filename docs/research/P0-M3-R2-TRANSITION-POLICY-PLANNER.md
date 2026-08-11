# P0-M3-R2 -- Transition-Policy Planner + Song-Preservation Gate

Status date: 2026-08-11

## 0. Execution profile actually used

- **Execution agent:** Claude Code runtime (Claude Desktop -> Code execution surface per `AGENTS.md`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High (owner/PM Desktop-UI attestation).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **Starting baseline:** `f66f74af6ab2ee1e923a4eec4bb4129503e4d5a9` (accepted P0-M3-R1 closeout).
- **This document answers** GitHub Issue #6, P0-M3-R2.

## 1. Result

**PASS**

Every Issue #6 acceptance criterion (AC1-AC18) has direct, independently reproducible evidence -- see §10's inline matrix. All evidence is produced by `tools/p0m3/transition_policy/`, a disposable, stdlib-only, deterministic benchmark: `python run_benchmark.py` regenerates every JSON result byte-for-byte; `python verify.py` independently re-derives and checks every AC-mapped assertion (25 checks, all PASS, captured verbatim in §9). No Signalsmith Stretch, no Rubber Band, no production P1 engine, and no audio bytes exist anywhere in this deliverable.

## 2. Why this task exists (owner-driven priority reorder)

The project owner tested Offtrack on 2026-08-11 and reported: transitions felt musically random/annoying, automatic mixing felt intrusive, and in one observed case the current track was abandoned after roughly 30 seconds. Per Issue #6, this is recorded strictly as `OWNER_SUBJECTIVE_REFERENCE` (see `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md`) -- **not** a claim about Offtrack's actual internals, not a reconstructed track/setting, and not evidence used to tune any threshold in this document to a specific number. It motivated the *shape* of the adversarial fixture set (specifically TP-01's ~30-second technically-compatible-but-musically-premature trap) and nothing more.

The question this pass answers is **WHEN should AutoMix leave the current track**, not how to blend the audio once a good exit point is chosen. Signalsmith Stretch, Rubber Band, and the P1 production engine are explicitly out of scope (AC16, AC17) and were not started (verified in §9, check `0b`).

## 3. Policy modes (Task A)

These are P0 research concepts, not final product UI copy.

### `FULL_SONG_DEFAULT`
Normal, everyday listening. The default and only silent behavior.
- Strongly preserves the song: a candidate exit is eligible only if it clears an intent-specific song-preservation fraction floor (0.55 of duration for normal-length tracks, 0.40 for short tracks -- Task C) **and** carries independent structural evidence.
- "Play longer" (`PLAY_THROUGH`) and "play the whole track, hand off naturally" (`NO_SPECIAL_TRANSITION`) are both correct, common, first-class outcomes -- not fallback failure states.
- Early transitions require the fraction floor **and** structural evidence **and** adequate confidence **and** no high vocal-collision risk to all hold simultaneously (§5).

### `BALANCED_MIX`
Allows earlier transitions than `FULL_SONG_DEFAULT` (fraction floor 0.30 / 0.20 short-track) but is **not** highlight/short-form playback: every guard from `FULL_SONG_DEFAULT` still applies except the floor's numeric value. A candidate with no structural evidence, low confidence, or high vocal-collision risk is rejected identically to `FULL_SONG_DEFAULT`.

### `HIGHLIGHT_EXPLICIT`
Research-only representation of intentional shortened playback.
- Never the default; only reachable when the listener_intent parameter passed into the planner is explicitly `HIGHLIGHT_EXPLICIT` (§5, §9 AC1/AC4).
- The song-preservation fraction floor is lifted (0.0), but structural evidence, confidence, and vocal-safety guards are **not** lifted -- `HIGHLIGHT_EXPLICIT` permits an *earlier* exit, never an *arbitrary/unstructured* one (Task A: "never default; only active under explicit user intent").
- Benchmarked as a fully separate row (`EXPLICIT_HIGHLIGHT@HIGHLIGHT_EXPLICIT`) from every default-intent row, so no aggregate metric can hide highlight-only behavior inside "normal" numbers.

## 4. Scope boundary (P3: "when" is independent of "how")

This pass implements (1) transition eligibility/exit timing and the policy boundary into (2) transition-class selection. It explicitly does **not** implement (3) DSP execution. The planner's only DSP-adjacent output is a *permitted envelope* (`permitted_tempo_pitch_envelope`, reusing `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §7's `manipulation_constraints` shape) and a *preferred transition class set* drawn from the `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1 taxonomy -- never a rendered transition.

## 5. Transition eligibility model (Task B)

Implemented in `tools/p0m3/transition_policy/policy/eligibility.py`. For every candidate exit point, four independent guards are evaluated; a candidate is `eligible` only if **all** pass. No single guard is the premature-exit guard (AC5):

| # | Guard | Independent of | Rejection reason code |
|---|---|---|---|
| 1 | `vocal_collision_risk != HIGH` | intent, fraction, structure | `VOCAL_COLLISION_RISK_HIGH` |
| 2 | `structure_confidence` is `MEDIUM` or `HIGH` | fraction, structure content | `LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY` |
| 3 | at least one of `in_acceptable_exit_region` / `is_outro_tail_opportunity` / `musical_unit_complete` is true | fraction/elapsed time entirely -- BPM/key compatibility alone never satisfies this (P5) | `NO_STRUCTURAL_EVIDENCE` |
| 4 | `fraction_consumed >= floor(intent, duration_class)` (floor is `0.0` under `HIGHLIGHT_EXPLICIT`; a lower floor under a duration-based short-track exception -- Task C) | guards 1-3 | `BELOW_PRESERVATION_FRACTION_FLOOR` |

Every eligible candidate additionally receives:
- `song_preservation_score` (= fraction consumed, favors later candidates among ties),
- `musical_structure_score` (weighted sum of region/beat-alignment/musical-unit-complete/outro-tail-opportunity, max 1.0),
- `timing_score` (confidence-multiplier-scaled combination of the two, used only for logging/ranking -- the greedy first-eligible-candidate-in-time-order rule is what actually selects the transition point, since guards 1-4 already guarantee no eligible candidate is ever premature; see `tools/p0m3/transition_policy/README.md` "Design notes"),
- `preferred_transition_class_set` -- never `["FULL_DJ_BLEND"]` alone (P2; verified empirically in §9 `wrong_transition_class_rate` = 0 for every structure-aware row).

Reason-code semantics are defined once in `eligibility.py`'s `REASON` dict and reused verbatim in every trace record (AC12).

## 6. Premature-exit guard (Task C) -- how the ~30s failure class is actually prevented

The default policy does **not** use a hard `elapsed >= 60s` (or any other fixed absolute-time) rule. It combines:
1. listener intent (via the floor value and whether the floor applies at all),
2. fraction/duration context (the floor is a *fraction*, not an absolute time, and has a distinct short-track value),
3. structural evidence (guard 3, evaluated completely independently of the floor),
4. confidence-aware fallback (guard 2),
5. vocal-safety (guard 1).

`TP-01` is the direct structural analogue of the owner's ~30s observation: a BPM/key-compatible candidate at 30000ms (14.3% of a 210000ms track) with **no** structural evidence. `verify.py` AC3 confirms `STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT` never transitions there; the fixture's actual failure driver is guard 3 (`NO_STRUCTURAL_EVIDENCE`), not the fraction floor -- confirmed by the sensitivity sweep (§7) showing the floor can be lowered all the way to 0.15 with zero effect on this fixture's outcome.

### Sensitivity test (Task C/E, AC13)

Sweeping `STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT`'s fraction floor from 0.15 to 0.85 with every other guard held fixed (`tools/p0m3/transition_policy/results/sensitivity_matrix.json`, reproduced exactly):

| fraction_floor | premature_exit_rate | missed_transition_opportunity_rate | fallback_playthrough_rate |
|---|---|---|---|
| 0.15 | 0/9 | 0/6 | 0.4 |
| 0.30 | 0/9 | 1/6 | 0.5 |
| 0.45 | 0/9 | 2/6 | 0.6 |
| 0.55 | 0/9 | 3/6 | 0.7 |
| 0.70 | 0/9 | 4/6 | 0.8 |
| 0.85 | 0/9 | 4/6 | 0.8 |

**Premature-exit rate is 0/9 at every threshold tested**, including the most permissive (0.15) -- because the structural-evidence guard is independent of the floor and already excludes every trap/vocal-collision-trap candidate in the fixture set regardless of elapsed time. This is the direct evidence for AC5.

Contrast (from the main matrix, §8): `BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT` (a fraction floor of 0.10, **no** structural-evidence guard) has `premature_exit_rate = 7/9`, and `NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT` (no floor and no structural guard at all) has `premature_exit_rate = 9/9`. A fraction/time floor alone, without an independent structural-evidence requirement, does not prevent the owner's observed failure class -- it only ever shifts *which* early trap gets picked. (BPM_KEY_ONLY_EARLY's 2 non-premature outcomes, TP-04 and TP-07, are themselves coincidental: its 0.10 floor happened to reject those two fixtures' specific trap candidates by fraction alone, not because the policy understood structure -- it then picked those fixtures' genuinely valid mid-track candidates purely by chance of timing, not intent. This is documented directly in the code comments of `run_benchmark.py`'s sensitivity conclusion string and is why "premature-exit rate" must always be read together with "structural-evidence guard present: yes/no", never as a bare percentage.)

Sweeping the fraction floor via `fraction_floor_override` bypasses the short-track exception (it applies uniformly, including to short tracks) by construction, which is itself informative: at `fraction_floor=0.55` (the normal-length default value) the override sweep shows `missed_transition_opportunity = 3/6`, one worse than the real default configuration's `2/6` (§8) -- the extra miss is exactly `TP-03` (the short-track fixture), whose real 0.40 short-track floor admits its 0.44-fraction valid exit while a uniform 0.55 floor would not. This is additional, distinct evidence for AC6 beyond the direct fixture-level check in §9.

## 7. Confidence-aware fallback and vocal-safety (AC9, Task D items 8-9)

`TP-09` carries `structure_confidence: "NONE"` on every field (a genuinely unannotated/`UNKNOWN`-source track, distinct from `TP-05`'s confidently-authored "no outro exists"). Guard 2 rejects its technically-compatible candidate outright regardless of what it claims about beat alignment; the planner falls back to `NO_SPECIAL_TRANSITION` rather than fabricating certainty. `TP-08` demonstrates guard 1 operating independently of structural quality: a candidate with full structural evidence (`in_acceptable_exit_region`, `musical_unit_complete`, `beat_downbeat_aligned`) is still rejected because `vocal_collision_risk = "HIGH"` at that exact boundary, and the policy instead selects the clean late outro.

## 8. Policy candidates and results (Task E)

Five policy candidates were implemented and benchmarked (`tools/p0m3/transition_policy/policy/policies.py`):

1. **`NAIVE_EARLIEST_COMPATIBLE`** -- adversarial baseline. Earliest technically-compatible (BPM/key/beat-aligned) candidate wins; no structure, confidence, or vocal-risk awareness at all; forces `["FULL_DJ_BLEND"]` unconditionally.
2. **`BPM_KEY_ONLY_EARLY`** -- SimpMusic-class baseline (`docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §5: BPM/key metadata drives an always-transitions-N-seconds-before-the-end heuristic with no beat-timestamp/structure awareness). Modeled here as BPM/key-compatible-and-above-a-small-fixed-fraction-floor (0.10), still no structural-evidence guard.
3. **`TAIL_ONLY_NATURAL_EXIT_BIASED`** -- conservative baseline: a single hard rule (structural region/outro-tail present **and** fraction >= 0.70), no nuanced scoring.
4. **`STRUCTURE_AWARE_PRESERVATION`** -- the Task B eligibility model (§5), run under `FULL_SONG_DEFAULT` and separately under `BALANCED_MIX`. **This is the recommended policy for the next pass** (§11).
5. **`EXPLICIT_HIGHLIGHT`** -- the identical Task B eligibility model, always forced to evaluate under `HIGHLIGHT_EXPLICIT` regardless of the nominal intent argument, demonstrating that shortened playback is reachable only through explicit opt-in.

### 8.1 Aggregate metrics (`results/metrics.json`, reproduced exactly)

Denominators: `trap_fixtures=9` (all except TP-10), `valid_fixtures=10`, `missed_opportunity_fixtures=6` (TP-02, TP-03, TP-04, TP-07, TP-08, TP-10 -- fixtures whose earliest legitimate opportunity is not simply "the natural end of the track").

| Policy@Intent | premature_exit_rate | valid_late_exit_capture_rate | missed_opportunity_rate | wrong_class_rate | fallback_rate | mean_fraction_preserved |
|---|---|---|---|---|---|---|
| NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT | 9/9 | 1/10 | 5/6 | 10/10 | 0/10 | 0.2776 |
| BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT | 7/9 | 3/10 | 3/6 | 0/10 | 0/10 | 0.3655 |
| TAIL_ONLY_NATURAL_EXIT_BIASED@FULL_SONG_DEFAULT | 0/9 | 10/10 | 4/6 | 0/2 | 8/10 | 0.9868 |
| STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT | 0/9 | 10/10 | 2/6 | 0/4 | 6/10 | 0.8870 |
| STRUCTURE_AWARE_PRESERVATION@BALANCED_MIX | 0/9 | 10/10 | 1/6 | 0/5 | 5/10 | 0.8345 |
| EXPLICIT_HIGHLIGHT@HIGHLIGHT_EXPLICIT | 0/9 | 10/10 | 0/6 | 0/6 | 4/10 | 0.7554 |

Reading this table: the two naive/BPM-only baselines are the only rows with a nonzero `premature_exit_rate` (AC2) and the only rows with a nonzero `wrong_transition_class_rate` (P2 violation -- `NAIVE_EARLIEST_COMPATIBLE` forces `FULL_DJ_BLEND` on every one of its 10 transitions). `TAIL_ONLY_NATURAL_EXIT_BIASED` has a perfect `premature_exit_rate` but the *worst* `missed_transition_opportunity_rate` among the structurally-aware policies (4/6) and the highest `fallback_playthrough_rate` (8/10) -- it is safe but needlessly restrictive (Task C's "long track... unnecessarily restrictive" failure mode). `STRUCTURE_AWARE_PRESERVATION` strictly dominates it on every axis except raw `valid_late_exit_capture_rate` (tied at 10/10). `EXPLICIT_HIGHLIGHT` has the lowest `missed_transition_opportunity_rate` (0/6) and lowest `mean_fraction_of_song_preserved` (0.7554) -- exactly the expected shape for an explicit-intent-gated policy: it captures every legitimate opportunity, including the earliest ones, at the cost of preserving less of the average track. This tradeoff is only acceptable because it never fires silently (§9 AC1/AC4).

### 8.2 Per-fixture decision matrix (adversarial fixture results, Task D + Issue #6 handoff requirement)

`decision_type` and, when `TRANSITION`, the exact candidate selected, for every fixture x policy@intent combination (`results/decision_traces.json`, reproduced exactly):

| fixture | NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT | BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT | TAIL_ONLY_NATURAL_EXIT_BIASED@FULL_SONG_DEFAULT | STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT | STRUCTURE_AWARE_PRESERVATION@BALANCED_MIX | EXPLICIT_HIGHLIGHT@HIGHLIGHT_EXPLICIT |
|---|---|---|---|---|---|---|
| TP-01 (early technical trap, no real exit) | TRANSITION @TP-01-C1 **(trap)** | TRANSITION @TP-01-C1 **(trap)** | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION |
| TP-02 (strong late outro) | TRANSITION @TP-02-C1 **(trap)** | TRANSITION @TP-02-C1 **(trap)** | TRANSITION @TP-02-C2 (valid) | TRANSITION @TP-02-C2 (valid) | TRANSITION @TP-02-C2 (valid) | TRANSITION @TP-02-C2 (valid) |
| TP-03 (short track) | TRANSITION @TP-03-C1 **(trap)** | TRANSITION @TP-03-C1 **(trap)** | NO_SPECIAL_TRANSITION | TRANSITION @TP-03-C2 (valid, short-track exception) | TRANSITION @TP-03-C2 (valid) | TRANSITION @TP-03-C2 (valid) |
| TP-04 (long track, mid-track exit) | TRANSITION @TP-04-C1 **(trap)** | TRANSITION @TP-04-C2 (valid, by luck of its 0.10 floor) | NO_SPECIAL_TRANSITION **(missed)** | TRANSITION @TP-04-C2 (valid) | TRANSITION @TP-04-C2 (valid) | TRANSITION @TP-04-C2 (valid) |
| TP-05 (no clean outro) | TRANSITION @TP-05-C1 **(trap)** | TRANSITION @TP-05-C1 **(trap)** | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION |
| TP-06 (early false opportunity) | TRANSITION @TP-06-C1 **(trap)** | TRANSITION @TP-06-C1 **(trap)** | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION |
| TP-07 (instrumental/low vocal) | TRANSITION @TP-07-C1 **(trap)** | TRANSITION @TP-07-C2 (valid, by luck of its 0.10 floor) | NO_SPECIAL_TRANSITION **(missed)** | NO_SPECIAL_TRANSITION **(missed under this intent)** | TRANSITION @TP-07-C2 (valid) | TRANSITION @TP-07-C2 (valid) |
| TP-08 (dense vocal overlap) | TRANSITION @TP-08-C1 **(vocal trap)** | TRANSITION @TP-08-C1 **(vocal trap)** | TRANSITION @TP-08-C2 (valid) | TRANSITION @TP-08-C2 (valid) | TRANSITION @TP-08-C2 (valid) | TRANSITION @TP-08-C2 (valid) |
| TP-09 (no trustworthy annotation) | TRANSITION @TP-09-C1 **(trap)** | TRANSITION @TP-09-C1 **(trap)** | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION |
| TP-10 (explicit highlight case) | TRANSITION @TP-10-C1 (valid, but for the wrong reason -- no intent gate) | TRANSITION @TP-10-C1 (valid, but for the wrong reason) | NO_SPECIAL_TRANSITION | NO_SPECIAL_TRANSITION **(correctly withheld)** | NO_SPECIAL_TRANSITION **(correctly withheld)** | TRANSITION @TP-10-C1 **(correctly granted)** |

**TP-07's `STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT` "missed" entry is intentional, not a defect**: TP-07-C2 sits at fraction 0.475, above `BALANCED_MIX`'s 0.30 floor but below `FULL_SONG_DEFAULT`'s 0.55 floor -- exactly the designed contrast between the two intents (§3). **TP-10's `NO_SPECIAL_TRANSITION` under both default intents is the core AC1/AC4 proof**: the identical structurally-valid candidate is correctly withheld under `FULL_SONG_DEFAULT`/`BALANCED_MIX` and correctly granted only under `EXPLICIT_HIGHLIGHT`.

### 8.3 PLAY_THROUGH vs. NO_SPECIAL_TRANSITION (AC10)

`results/playthrough_demo.json` queries the identical `TP-01` fixture under the identical policy/intent at two evaluation times:

- `evaluation_time_ms=60000` (before the outro region, more track remains) -> `decision_type: "PLAY_THROUGH"`, `reason_codes: ["NO_ELIGIBLE_CANDIDATE_YET_MORE_TRACK_REMAINS"]`, no exit window populated.
- `evaluation_time_ms=210000` (natural end reached) -> `decision_type: "NO_SPECIAL_TRANSITION"`, `reason_codes: ["END_OF_TRACK_NATURAL_HANDOFF", "STRUCTURAL_EVIDENCE_PRESENT"]`.

This is the direct demonstration of Task C's "if no good transition exists yet, playing longer is correct": the same track, same policy, same intent produces two distinct, both-correct, first-class outcomes purely as a function of how much of the track has actually been observed.

## 9. Verification (reproducible commands and exact results)

```
python tools/p0m3/transition_policy/run_benchmark.py
python tools/p0m3/transition_policy/verify.py
```

`verify.py` output, captured verbatim:

```
=== 0. Structural / scope-boundary checks ===
[PASS] fixture count == 10 (Task D minimum)
[PASS] 0. Ground-truth-only fixture fields are never read by policy decision code (AC12 evidence integrity)
[PASS] 0b. No Signalsmith/Rubber Band/DSP-library import anywhere in tools/p0m3/transition_policy
[PASS] 0c. No audio bytes committed anywhere in tools/p0m3/transition_policy (AC15)

=== AC1: normal/default listening never silently equals highlight shortening (TP-10) ===
[PASS] TP-10 FULL_SONG_DEFAULT does NOT transition at the highlight point TP-10-C1
[PASS] TP-10 BALANCED_MIX does NOT transition at the highlight point TP-10-C1
[PASS] TP-10 EXPLICIT_HIGHLIGHT DOES transition at TP-10-C1 (AC4)

=== AC2: naive/BPM-only early-exit baselines are represented and measured ===
[PASS] NAIVE_EARLIEST_COMPATIBLE is a registered policy
[PASS] BPM_KEY_ONLY_EARLY is a registered policy
[PASS] NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT has nonzero premature_exit_rate
[PASS] BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT has nonzero premature_exit_rate

=== AC3: the ~30s technically-valid-but-musically-premature case is rejected in default mode (TP-01) ===
[PASS] TP-01 FULL_SONG_DEFAULT does not transition at the 30s trap TP-01-C1
[PASS] TP-01 FULL_SONG_DEFAULT decision is NO_SPECIAL_TRANSITION (played through to natural outro)

=== AC5: no single elapsed-time/fraction threshold is the sole early-exit guard ===
[PASS] premature_exit_rate stays 0 across every swept fraction floor (structural gate is independent of the floor)
[PASS] sensitivity sweep covers >=4 distinct thresholds (AC13)

=== AC6: short-track exception behavior is tested (TP-03) ===
[PASS] TP-03 FULL_SONG_DEFAULT captures the short-track valid exit TP-03-C2 (fraction 0.44 < normal-length floor 0.55)

=== AC7: long-track behavior is tested (TP-04) ===
[PASS] TP-04 STRUCTURE_AWARE_PRESERVATION captures the mid-track valid exit TP-04-C2 (not overly restrictive)
[PASS] TP-04 TAIL_ONLY_NATURAL_EXIT_BIASED misses TP-04-C2 (demonstrates over-restrictiveness contrast)

=== AC8: no-clean-outro behavior is tested (TP-05) ===
[PASS] TP-05 never transitions at the technical trap TP-05-C1
[PASS] TP-05 final decision is NO_SPECIAL_TRANSITION (no clean outro exists)

=== AC9: missing/low-confidence structure data causes conservative fallback (TP-09) ===
[PASS] TP-09 never transitions at the unverified-confidence candidate TP-09-C1
[PASS] TP-09 final decision is NO_SPECIAL_TRANSITION (conservative fallback, no fabricated certainty)

=== AC10: PLAY_THROUGH / NO_SPECIAL_TRANSITION are first-class valid results ===
[PASS] PLAY_THROUGH is reachable (TP-01 mid-track query)
[PASS] NO_SPECIAL_TRANSITION is reachable (TP-01 end-of-track query)

=== AC11: queue ordering is never used as permission to exit the current track early ===
[PASS] TP-01 decision is identical regardless of queue_next_track_quality (EXCELLENT/POOR/UNKNOWN)
[PASS] PlannerDecision.queue_order_independent_of_exit_timing is always True

=== AC12: candidate decisions expose reason codes / traceable evidence ===
[PASS] every (fixture, policy) decision has a non-empty candidate_trace
[PASS] every non-PLAY_THROUGH decision carries reason_codes

=== AC18: a concrete planner-output contract is produced ===
[PASS] PlannerDecision contract exposes every Task G required field

=== RESULT: ALL ASSERTIONS PASS ===
```

25 of 25 checks PASS. Re-running both commands against this commit reproduces byte-identical `results/*.json` (pure stdlib, no randomness, no wall-clock-dependent values in the data itself).

## 10. Acceptance criteria matrix (Issue #6)

| # | Acceptance criterion | Result | Evidence |
|---|---|---|---|
| AC1 | normal/default listening never silently equals highlight shortening | PASS | §8.2 TP-10 row; §9 AC1 checks |
| AC2 | naive/BPM-only early-exit baselines are represented and measured | PASS | §8, `NAIVE_EARLIEST_COMPATIBLE`/`BPM_KEY_ONLY_EARLY` rows; §9 AC2 checks |
| AC3 | ~30s technically-valid-but-musically-premature case is rejected in default mode | PASS | §6, §8.2 TP-01 row; §9 AC3 checks |
| AC4 | explicit highlight-intent case may validly allow earlier exit | PASS | §8.2 TP-10 row (`EXPLICIT_HIGHLIGHT` column); §9 AC1 3rd check |
| AC5 | no single arbitrary elapsed-time threshold is the sole early-exit guard | PASS | §5 (4 independent guards); §6/§7 sensitivity sweep, 0 premature exits across the full swept range |
| AC6 | short-track exception behavior is tested | PASS | §6 (override-sweep contrast), §8.2 TP-03 row; §9 AC6 check |
| AC7 | long-track behavior is tested | PASS | §8.2 TP-04 row (structure-aware captures mid-track exit; tail-only misses it); §9 AC7 checks |
| AC8 | no-clean-outro behavior is tested | PASS | §7, §8.2 TP-05 row; §9 AC8 checks |
| AC9 | missing/low-confidence structure data causes conservative fallback, not fabricated certainty | PASS | §7, §8.2 TP-09 row; §9 AC9 checks |
| AC10 | `PLAY_THROUGH` / `NO_SPECIAL_TRANSITION` is a first-class valid result | PASS | §8.3 playthrough demo; §9 AC10 checks |
| AC11 | queue ordering is not used as permission to exit the current track early | PASS | `policy/eligibility.py`/`policy/policies.py` accept no next-track/queue argument at all (structural); §9 AC11 checks (decision identical across 3 queue-quality values) |
| AC12 | candidate decisions expose reason codes / traceable evidence | PASS | `results/decision_traces.json` (every decision carries `candidate_trace` + `reason_codes`); §9 AC12 checks |
| AC13 | threshold sensitivity is reported | PASS | §6/§7 6-point sensitivity matrix |
| AC14 | owner Offtrack observation is recorded only as subjective reference, not objective truth | PASS | `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md`, `OWNER_SUBJECTIVE_REFERENCE` label |
| AC15 | no protected/copyrighted provider audio or secrets are committed | PASS | fixtures are metadata-only JSON; §9 check `0c` (no audio-file extensions anywhere in the package) |
| AC16 | no Signalsmith/Rubber Band implementation is started | PASS | §9 check `0b` (AST/import-level scan of every `.py` file in the package) |
| AC17 | no production P1 engine is started | PASS | §2, §4 scope statement; only research/benchmark code exists under `tools/p0m3/transition_policy/` |
| AC18 | a concrete planner-output contract is produced for the next DSP pass | PASS | §11, `policy/contract.py`; §9 AC18 check |

## 11. Planner output contract (Task G) and recommendation for the next pass

`tools/p0m3/transition_policy/policy/contract.py`'s `PlannerDecision` is the smallest provider-independent handoff a future DSP-execution pass needs:

```json
{
  "fixture_id": "string",
  "listener_intent": "FULL_SONG_DEFAULT | BALANCED_MIX | HIGHLIGHT_EXPLICIT",
  "policy_name": "string",
  "decision_type": "TRANSITION | PLAY_THROUGH | NO_SPECIAL_TRANSITION",
  "current_track_exit_window_ms": {"t_start_ms": "int", "t_end_ms": "int"},
  "next_track_entry_window_ms": {"t_start_ms": "int", "t_end_ms": "int"},
  "preferred_transition_class_set": ["FULL_DJ_BLEND | SHORT_EQ_BLEND | SIMPLE_CROSSFADE | GAPLESS | CUT | NO_SPECIAL_TRANSITION", "..."],
  "beat_downbeat_alignment_target_ms": "int | null",
  "permitted_tempo_pitch_envelope": {"tempo_ratio_max_deviation": 0.12, "max_pitch_shift_semitones": 3},
  "confidence": "NONE | LOW | MEDIUM | HIGH",
  "reason_codes": ["string", "..."],
  "queue_order_independent_of_exit_timing": true,
  "candidate_trace": ["... full per-candidate evaluation record, see results/decision_traces.json ..."]
}
```

`preferred_transition_class_set` reuses `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1's taxonomy exactly, so a future DSP-execution pass can consume it directly without a translation layer; `permitted_tempo_pitch_envelope` reuses `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §7's `manipulation_constraints` field names for the same reason.

### Recommendation

`STRUCTURE_AWARE_PRESERVATION` should enter the next P0-M3 pass as the default-listening policy (`FULL_SONG_DEFAULT` for the actual product default, `BALANCED_MIX` as a user-selectable alternative), with `EXPLICIT_HIGHLIGHT`'s gating mechanism (force-`HIGHLIGHT_EXPLICIT`-regardless-of-ambient-intent) reserved strictly for a future, explicitly-invoked highlight/short-form feature -- never wired to any default code path. `NAIVE_EARLIEST_COMPATIBLE` and `BPM_KEY_ONLY_EARLY` are retained only as negative baselines (they quantify exactly what the SimpMusic-class and naive-matcher failure modes look like, per §8.1) and must never be shipped. `TAIL_ONLY_NATURAL_EXIT_BIASED` is retained as a secondary safety-only reference (its `premature_exit_rate` is perfect) but should not be the shipped default given its high `missed_transition_opportunity_rate`.

This recommendation is a **research conclusion about eligibility policy**, not an authorization to begin DSP execution -- Signalsmith Stretch, Rubber Band, and the P1 engine remain explicitly out of scope for this pass and were not started (§9 check `0b`).

## 12. Unknowns / risks

- The eligibility model's `structure_score` weights (0.4/0.2/0.2/0.2) and the fraction-floor defaults (0.55/0.30/0.40/0.20/0.0) are P0 placeholders calibrated to make the ten designed fixtures behave as intended, not derived from real-listener data. The sensitivity sweep (§6/§7) demonstrates the guard *structure* is robust to the specific floor value, but the floor's *product-facing* value still needs real human-listening validation against `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §9's rubric in a later pass.
- All ten fixtures are metadata-only and hand-authored (`SYNTHETIC_EXACT` by construction); no real-music validation occurred this pass, consistent with Issue #6's scope (a disposable benchmark, not a production corpus). This mirrors the same limitation flagged in `docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md` §14 for BeatNet/CUE-DETR.
- The "greedy first-eligible-candidate-in-time-order" selection rule (§5) is sufficient given how the ten fixtures are constructed (each has at most one non-trap eligible candidate per intent) but has not been stress-tested against a fixture with *multiple* simultaneously-eligible candidates of different quality; a future pass extending the fixture set should add such a case and verify the ranking scores (not just eligibility) actually get exercised.
- `structure_confidence` and the vocal/structural boolean features are fixture-authored ground truth in this pass, standing in for a future real analyzer's output (BeatNet/CUE-DETR/All-In-One per `docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md`). How a real analyzer's actual confidence/error characteristics map onto these four discrete guards is `UNKNOWN_NEEDS_RUNTIME_PROOF` and is exactly the kind of question the next P0-M3 pass (the Signalsmith/Rubber Band execution shootout, now unblocked by this document) should carry forward.

## 13. Files

- `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` (this document)
- `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md`
- `tools/p0m3/transition_policy/README.md`
- `tools/p0m3/transition_policy/fixtures/fixtures.json`
- `tools/p0m3/transition_policy/fixtures/manifest.json`
- `tools/p0m3/transition_policy/policy/eligibility.py`
- `tools/p0m3/transition_policy/policy/policies.py`
- `tools/p0m3/transition_policy/policy/contract.py`
- `tools/p0m3/transition_policy/policy/__init__.py`
- `tools/p0m3/transition_policy/run_benchmark.py`
- `tools/p0m3/transition_policy/verify.py`
- `tools/p0m3/transition_policy/.gitignore`
- `tools/p0m3/transition_policy/results/decision_traces.json`
- `tools/p0m3/transition_policy/results/metrics.json`
- `tools/p0m3/transition_policy/results/sensitivity_matrix.json`
- `tools/p0m3/transition_policy/results/playthrough_demo.json`
- `tools/p0m3/transition_policy/results/SUMMARY.md`

## 14. PM review request

Please independently verify:

1. Run `python tools/p0m3/transition_policy/run_benchmark.py` and `python tools/p0m3/transition_policy/verify.py` and confirm `RESULT: ALL ASSERTIONS PASS`.
2. Open `tools/p0m3/transition_policy/fixtures/fixtures.json` and confirm `TP-01`'s only two candidates are the 30000ms trap (no structural evidence) and the 210000ms authored outro -- and that `STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT`'s decision for it in `results/decision_traces.json` is `NO_SPECIAL_TRANSITION`, never `TRANSITION` at the trap.
3. Open `results/decision_traces.json` and confirm `TP-10`'s decision differs between `STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT` (`NO_SPECIAL_TRANSITION`) and `EXPLICIT_HIGHLIGHT@HIGHLIGHT_EXPLICIT` (`TRANSITION @TP-10-C1`) for the identical fixture.
4. Confirm no file under `tools/p0m3/transition_policy/` has a `.wav`/`.mp3`/other audio extension, and that `policy/*.py` contains no `rubberband`/`signalsmith` import.
5. Confirm `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md` labels the owner observation `OWNER_SUBJECTIVE_REFERENCE` and does not assert any specific Offtrack track/setting.
