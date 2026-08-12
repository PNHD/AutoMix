# P0-M3-R2 -- Apple-like Near-End Transition Planner + Compatibility Gate

Status date: 2026-08-12

## 0. Execution profile actually used

- **Execution agent:** Claude Code runtime (Claude Desktop -> Code execution surface per `AGENTS.md`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High (owner/PM Desktop-UI attestation).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **Starting point:** HEAD `e9fb5d025e3aad3a2777292b54c720449438e231` (the prior P0-M3-R2 pass), redesigned per the newest binding comment on Issue #6.
- **This document answers** GitHub Issue #6's **"PM PRODUCT DIRECTION UPDATE -- APPLE-LIKE NEAR-END LISTENING TARGET"** comment, which explicitly supersedes the prior "PM REVIEW -- REPAIR REQUIRED" comment on the same issue (the prior repair prompt was never executed as a standalone task, per the owner's instruction).

## 1. What changed and why (supersession summary)

The previous pass modeled song-preservation as `fraction_consumed` (elapsed time / duration) and picked the first eligible candidate in array order. The newest PM direction identifies two defects with that model:

1. **Fraction-consumed conflates "transition starts" with "song was cut."** A transition that begins overlapping the next track 20-40 seconds before a song's natural end, while the outgoing track keeps playing through the overlap, is a *correct* Apple-like outcome -- not a truncation. The old model had no way to represent that distinction.
2. **First-eligible-candidate-wins is not a ranked planner.** If multiple near-end candidates are eligible, the planner must pick the *best* one (by preservation, structural/outro quality, pair compatibility, energy), not merely whichever the fixture's candidate array happens to list first.

This redesign replaces `fraction_consumed` with an explicit **overlap-bounded preservation model** (`policy/metrics.py`), adds a **pair-level mixability gate** (`policy/compatibility.py`) so `FULL_DJ_BLEND` is never forced by timing alone, and adds a **deterministic, order-invariant ranking** among all eligible near-end candidates (`policy/ranking.py`). The product-default policy is renamed `SEAMLESS_FULL_TRACK_DEFAULT` -- the only current product-default candidate; `BALANCED_MIX` and `HIGHLIGHT_EXPLICIT` are retained strictly as research/negative controls that never influence default behavior.

## 2. Apple-like behavioral target -- public evidence vs. project inference

Per the newest PM comment, this section is split into three explicitly labeled tiers. Nothing in tier 3 is attributed to Apple.

### PUBLIC_APPLE_EVIDENCE

Retrieved 2026-08-12, quoted/paraphrased directly from primary sources:

- **Apple Support, "Transition songs in Music on iPhone"** (`support.apple.com/guide/iphone/iphadf2fe1f4/ios`): *"AutoMix automatically selects the best transition, depending on the music. For example, AutoMix might remove silence at the beginning and end of a track, or perform a simple crossfade, rather than a more complex transition, when appropriate."* *"Albums and some genres play without transitions."* AutoMix is on by default (iOS 26+, Apple Music catalog), toggle lives at Settings > Apps > Music > Song Transitions.
- **Apple Support, "How to turn AutoMix or Crossfade on or off in the Apple Music app"** (`support.apple.com/en-us/105067`): documents the Settings path and the AutoMix/Crossfade toggle; does not disclose internal timing/percentage logic.
- **Apple Newsroom, June 2025** ("Apple services deliver powerful features and intelligent updates to users this fall"): *"AutoMix, which mixes one song into the next, just like a DJ... Using AI to analyze audio features, it crafts unique transitions between songs with time stretching and beat matching to deliver continuous playback and an even more seamless listening experience."* Launched with iOS 26, on by default, iPhone 11+.
- **Apple Newsroom, June 2026** ("Apple unveils innovative features and intelligence experiences across services", iOS 27 cycle): *"AutoMix has added a whole new layer of energy and excitement to the experience with even better transitions that feel more immersive and engaging for listeners. AutoMix will also be available on Apple Music in tvOS and on HomePod."* No new mechanism, percentage, or timing number is disclosed.
- **Reputable hands-on report** (BGR, "AutoMix Is Apple Music's Worst Feature (And You Need To Turn It Off)"): critical piece, but observationally consistent with the "near-end, not mid-song" framing -- describes AutoMix initiating transitions *near the end of songs*, sometimes overlapping a fade-out or final chords, not abandoning a song mid-track. This is cited only for **observable behavior pattern**, not as proof of any internal threshold.

None of these sources disclose an exact percentage (e.g. 95%, 98%) or a fixed seconds-before-end number. This document does not claim one on Apple's behalf.

### OWNER_OBSERVED_TARGET

- Product target is **Apple-like normal consumer listening**, explicitly **not** a DJ app and **not** Offtrack-style highlight/short-form playback.
- Transitions should subjectively occur near a song's end, not at an arbitrary mid-song point purely because a technical mix point exists.
- A ~7-minute normal song automatically abandoned around ~2 minutes is a **catastrophic failure**, independent of how technically smooth the transition itself is.
- A transition beginning ~20-40 seconds before a song's natural end, with the outgoing track still audible through nearly all of its meaningful content, is potentially **correct**.
- The owner likes the energy/momentum feeling a more aggressive mixer can create, but only as a signal that applies *after* preservation and pair-compatibility safety gates already pass -- never as a justification for leaving a song early, over-stretching tempo, forcing incompatible genres, or accepting vocal-on-vocal collisions.

### PROJECT_INFERENCE_BENCHMARK_PROPOSAL

Everything below is this project's own benchmark design, not an Apple claim:

- `outgoing_content_preservation_ratio` is the load-bearing default-mode metric (not `transition_onset_ratio`).
- Preferred band: `0.97-1.00`. Acceptable P0 default-candidate band: `0.95-1.00`. Catastrophic ceiling: `< 0.90` without an explicit authored exception (e.g. verified non-musical dead air).
- `NEAR_END_MAX_OVERLAP_MS = 40000` (a P0 placeholder bound on how much overlap the planner will ever propose) -- chosen to sit inside the owner's own "20-40 seconds" example, not derived from any Apple disclosure.
- The pair-compatibility component set (genre/style, tempo, beat, downbeat, harmonic, energy, structure, vocal/bass collision, intro/outro texture, analysis confidence) and its specific thresholds (`MAX_JUSTIFIED_TEMPO_STRETCH_PCT = 0.12`, half/double-time tolerance `0.03`) are this project's clean-room quality gate.

## 3. Product target -- not a DJ app, not highlight playback

The recommended and only current product default is:

**`SEAMLESS_FULL_TRACK_DEFAULT`**

`BALANCED_MIX` and `HIGHLIGHT_EXPLICIT` are retained exclusively as research/negative controls (`policy/policies.py`'s `BALANCED_MIX_RESEARCH_CONTROL` and `EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL`). Neither influences the recommended engine's behavior -- they are independently computed rows in the benchmark matrix, never consulted by `SEAMLESS_FULL_TRACK_DEFAULT`'s own decision path (verified structurally, §9).

## 4. Core metric repair -- separating transition onset from song preservation

Implemented in `tools/p0m3/transition_policy/policy/metrics.py`.

| Field | Meaning |
|---|---|
| `effective_content_end_ms` | The meaningful musical ending. Equals `duration_ms` **unless** the fixture explicitly annotates `trailing_dead_air_is_authored_non_musical: true`, in which case `trailing_dead_air_ms` is subtracted. An unannotated tail is never silently treated as removable dead air (TP-05, TP-13 -- §8). |
| `transition_onset_ms` | When incoming content first becomes materially audible (the candidate's `t_ms`, bounded by `effective_content_end_ms`). |
| `transition_onset_ratio` | `transition_onset_ms / effective_content_end_ms`. |
| `overlap_duration_ms` | `min(NEAR_END_MAX_OVERLAP_MS, remaining_content_at_onset_ms)` -- bounded by both a plausibility ceiling and by the content that actually exists. |
| `outgoing_last_audible_ms` | `transition_onset_ms + overlap_duration_ms` -- when the outgoing track's meaningful content actually stops being audible. |
| `outgoing_content_preservation_ratio` | `outgoing_last_audible_ms / effective_content_end_ms`. **The load-bearing default-mode metric.** |
| `outgoing_content_lost_ms` | `effective_content_end_ms - outgoing_last_audible_ms`. |

This directly implements "transition onset may be earlier than 95% of the track if the outgoing track keeps playing naturally during the overlap": a candidate whose remaining content at onset is fully covered by `overlap_duration_ms` gets `outgoing_content_preservation_ratio == 1.0` regardless of how early its onset ratio is (see TP-11's near-end candidate, §8: onset ratio 0.94, preservation ratio 1.0). Conversely, a candidate far from the end cannot be rescued by an unrealistically long overlap, because overlap is bounded by both the plausibility ceiling and the actual remaining content -- this is what makes a ~2-minute exit on a 7-minute track measure as catastrophic (preservation ratio ~0.40, §8) without any special-cased "if near 2 minutes, reject" rule.

## 5. Near-end eligibility model

Implemented in `tools/p0m3/transition_policy/policy/eligibility.py`. Four independent guards, all must pass:

| # | Guard | Independent of | Rejection reason code |
|---|---|---|---|
| 1 | `vocal_collision_risk != HIGH` | intent, structure, preservation | `VOCAL_COLLISION_RISK_HIGH` |
| 2 | `structure_confidence` is `MEDIUM` or `HIGH` | preservation, structure content | `LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY` |
| 3 | at least one of `in_acceptable_exit_region` / `is_outro_tail_opportunity` / `musical_unit_complete` | elapsed time/preservation entirely -- BPM/key alone never satisfies this (P5) | `NO_STRUCTURAL_EVIDENCE` |
| 4 | `outgoing_content_preservation_ratio >= floor(intent)` | guards 1-3 | `BELOW_PRESERVATION_FLOOR` (+`CATASTROPHIC_PRESERVATION_LOSS` if `< 0.90`) |

Preservation floors: `SEAMLESS_FULL_TRACK_DEFAULT = 0.95` (project benchmark default, sensitivity-tested §7), `BALANCED_MIX = 0.65` (research/negative-control value only, no acceptance criterion), `HIGHLIGHT_EXPLICIT = 0.0` (bypassed by explicit intent; guards 1-3 still apply -- HIGHLIGHT_EXPLICIT permits an earlier exit, never an unstructured one).

`sequential_album_intent: true` (fixture-level) additionally strips `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` from the candidate's base transition-class set regardless of timing or pair-compatibility quality (TP-14, §8) -- sequential albums are preserved, not DJ-mixed.

## 6. Near-end candidate ranking -- no more first-eligible-wins

Implemented in `tools/p0m3/transition_policy/policy/ranking.py`. `decide()` (the canonical full-track/offline planner) evaluates **every** non-end candidate, collects all eligible ones, and ranks them by a documented lexicographic tuple:

1. `outgoing_content_preservation_ratio` (rounded to 2 decimals) descending
2. `musical_structure_score` descending
3. `energy_continuity_priority` descending
4. `confidence` rank descending
5. `candidate_id` (lexicographic) -- final deterministic tie-break, never based on array position or `t_ms`

`TP-12` (letter D) has two simultaneously eligible near-end candidates that both reach `outgoing_content_preservation_ratio == 1.0` -- X (earlier, `musical_structure_score 0.8`) and Y (later, true authored outro, `musical_structure_score 1.0`). The ranked planner selects Y under every candidate-array ordering tested: normal, reversed, and two independently-seeded shuffles (`results/order_invariance.json`, reproduced in §7). A first-eligible-wins planner would select X in array order and Y under a reversed/shuffled order -- exactly the order-dependent bug class this redesign removes.

`decide_at_time()` remains the **time-local** query primitive (cannot see future candidates, so it necessarily stays greedy first-eligible-seen-so-far) -- it is explicitly never presented as equivalent to the ranked full-track plan (spec "FULL-TRACK VS TIME-LOCAL"; §8.3 demonstrates its `PLAY_THROUGH`/`NO_SPECIAL_TRANSITION` role).

## 7. Pair compatibility gate

Implemented in `tools/p0m3/transition_policy/policy/compatibility.py`. Ten independent, individually-reported components (never collapsed into one opaque score): `genre_compatibility`, `tempo_compatibility` (direct / half-double / excessive-stretch), `required_tempo_stretch_pct`, `beat_compatibility`, `downbeat_compatibility`, `harmonic_compatibility`, `energy_continuity`, `structure_compatibility`, `vocal_collision_risk`, `bass_percussion_collision_risk`, `intro_outro_texture_compatibility`, `analysis_confidence`. `overall_dynamic_mix_eligible` is `true` only when every hard-gating component passes; `downgrade_transition_class_set()` intersects the timing-derived class set with what compatibility actually supports and never adds classes back.

`FULL_DJ_BLEND` is withheld by default whenever no `pair` is supplied to `decide()` at all -- compatibility must be *demonstrated*, not assumed (spec section D, "extremely suitable songs").

### 7.1 Pair fixture results (`results/pair_compatibility.json`, reproduced exactly)

| Pair | Letter | Purpose | Expected eligible | Computed eligible | TP-11 integration: `FULL_DJ_BLEND` offered |
|---|---|---|---|---|---|
| PAIR-01 | G | compatible genre + tempo + stable beat | True | True | True (`['FULL_DJ_BLEND', 'SHORT_EQ_BLEND', 'SIMPLE_CROSSFADE']`) |
| PAIR-02 | H | genre families share no overlap despite BPM matching exactly | False | False | False (`['SIMPLE_CROSSFADE']`) |
| PAIR-03 | I | tempo relation requires excessive stretch (0.556 > 0.12 ceiling) | False | False | False (`['SIMPLE_CROSSFADE']`) |
| PAIR-04 | J | genre/tempo compatible, dense vocal-on-vocal overlap | False | False | False (`['SIMPLE_CROSSFADE']`) |
| PAIR-05 | K | every gate passes, energy continuity STRONG | True | True | True (`['FULL_DJ_BLEND', 'SHORT_EQ_BLEND', 'SIMPLE_CROSSFADE']`) |

`incompatible_pair_downgrade_rate = 3/5 (0.6)`. The "TP-11 integration" column reuses TP-11's already-excellent near-end timing candidate for every row, varying only the pair -- proving pair compatibility gates `FULL_DJ_BLEND` **independently of timing quality** (PAIR-02 in particular: BPM matches exactly, beat/downbeat/analysis confidence are all HIGH, only genre is incompatible, and `FULL_DJ_BLEND` is still withheld -- direct evidence that BPM alone never authorizes complex mixing, P5).

## 8. Required adversarial fixtures (letters A-N, 14 timing fixtures + 5 pair fixtures)

Full mapping in `tools/p0m3/transition_policy/fixtures/manifest.json`'s `spec_letter_coverage`. Six additional fixtures (TP-02, 05, 06, 07, 08, 10) are retained from the prior pass as positive-capture/contrast controls per the PM comment's "retain existing TP cases" instruction.

| Letter | Fixture | Result |
|---|---|---|
| A | TP-01: 3-4min track, ~30s technical trap, no legit exit | Rejected (`NO_STRUCTURAL_EVIDENCE`); falls through to authored outro -> `NO_SPECIAL_TRANSITION` |
| B | TP-11: 7-min song, candidate at ~2m10s | Rejected: preservation ratio **0.405** (< 0.90 catastrophic ceiling) |
| C | TP-11: same song, near-end window (final ~25s) | Selected: preservation ratio **1.0** |
| D | TP-12: two eligible near-end candidates, X earlier / Y stronger | Y selected under all 3 tested orderings (normal/reversed/shuffled) -- see §6/§9 |
| E | TP-03: 60-90s short track | Selected at 33000ms (44% of duration) -- overlap-bounded model naturally admits it (remaining 42000ms fully covered by the 40000ms overlap ceiling, preservation ratio 0.973); no separate short-track fraction floor is needed |
| F | TP-04: 8-min long track | Mid-track candidate at 270000ms (56%) now correctly **rejected** (preservation 0.646); near-end candidate at 445000ms (35s before end, deliberately outside a naive fixed-30s-before-end window) **selected**; `FIXED_SECONDS_BEFORE_END_ONLY` baseline misses it, proving a fixed-seconds rule fails on long tracks (and on TP-03's short track too) |
| G-K | PAIR-01..05 | See §7.1 |
| L | TP-09: no trustworthy confidence annotation | Rejected (`LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY`) -> `NO_SPECIAL_TRANSITION` |
| M | TP-13: outro at 210000ms + 40000ms authored dead air (`duration_ms=250000`) | `effective_content_end_ms == 210000` (not 250000); selected candidate preservation ratio **1.0** -- dead air trimmed, outro never reported as truncated |
| N | TP-14: `sequential_album_intent: true`, otherwise-ideal near-end candidate + a fully compatible pair supplied | `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` withheld regardless; only `SIMPLE_CROSSFADE`-class transitions offered |

## 9. Verification (reproducible commands and exact results)

```
python tools/p0m3/transition_policy/run_benchmark.py
python tools/p0m3/transition_policy/verify.py
```

`verify.py`'s full output is reproduced verbatim in `tools/p0m3/transition_policy/results/SUMMARY.md`'s companion run log and in the PM handoff; **66 of 66 assertions PASS**, covering: 7-minute/~2-minute catastrophic-reject regression, preservation-floor-vs-catastrophic-ceiling check across every `SEAMLESS_FULL_TRACK_DEFAULT` transition, first-eligible-wins regression (TP-12), order-invariance (including an independently-reseeded shuffle beyond the cached results file), BPM-alone-never-authorizes-complex-mixing (PAIR-02), incompatible-genre/excessive-stretch-never-forced (PAIR-02/03), vocal-collision-never-ignored (PAIR-04, TP-08), missing-confidence-never-fabricated (TP-09, plus a pair-level LOW-confidence check), highlight-never-default (TP-10 across all three intents plus the R1 intent-mismatch guard), onset-never-truncation (TP-11), and outro-never-trimmed-as-dead-air (TP-13 vs. TP-05 contrast). All retained AC1-AC18 coverage from the original Issue #6 task body is re-verified under the new naming (§10).

## 10. Sensitivity analysis (preservation floor: 0.90 / 0.93 / 0.95 / 0.97 / 0.98)

`results/sensitivity_matrix.json`, reproduced exactly:

| preservation_floor | band | premature_exit_rate | missed_opportunity_rate | fallback_rate |
|---|---|---|---|---|
| 0.90 | at_catastrophic_ceiling | 0/10 | 1/9 | 0.4286 |
| 0.93 | at_catastrophic_ceiling | 0/10 | 1/9 | 0.4286 |
| 0.95 | acceptable_p0_default_candidate_band | 0/10 | 1/9 | 0.4286 |
| 0.97 | preferred_band_lower_bound | 0/10 | 1/9 | 0.4286 |
| 0.98 | preferred_band | 0/10 | 2/9 | 0.5000 |

`premature_exit_rate` is 0/10 at every tested floor, including the strict 0.90 ceiling itself -- because the structural-evidence guard (§5 guard 3) and vocal-collision guard (guard 1) are independent of the preservation floor and already exclude every trap candidate regardless of preservation ratio. This is the direct evidence that no single preservation-ratio threshold is, by itself, the premature-exit guard. Raising the floor from 0.95 to 0.98 costs one additional missed opportunity (1/9 -> 2/9) and raises the fallback rate -- the expected, monitored tradeoff of tightening toward the preferred band.

## 11. Policy/baseline comparison (`results/metrics.json`, reproduced exactly)

Denominators: `trap_fixtures=10`, `valid_fixtures=14`, `missed_opportunity_fixtures=9`.

| Policy@Intent | premature_exit | catastrophic/transitions | valid_capture | missed_opportunity | forced_FULL_DJ_BLEND | fallback | mean_preservation |
|---|---|---|---|---|---|---|---|
| NAIVE_EARLIEST_COMPATIBLE@SEAMLESS_FULL_TRACK_DEFAULT | 10/10 | 13/14 | 4/14 | 6/9 | 0/14 | 0/14 | 0.4000 |
| BPM_KEY_ONLY_EARLY@SEAMLESS_FULL_TRACK_DEFAULT | 8/10 | 13/14 | 4/14 | 6/9 | 0/14 | 0/14 | 0.4628 |
| TAIL_ONLY_NATURAL_EXIT_BIASED@SEAMLESS_FULL_TRACK_DEFAULT | 0/10 | 2/7 | 14/14 | 3/9 | 0/7 | 7/14 | 0.9465 |
| FIXED_SECONDS_BEFORE_END_ONLY@SEAMLESS_FULL_TRACK_DEFAULT | 0/10 | 1/5 | 14/14 | 5/9 | 0/5 | 9/14 | 0.9702 |
| **SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT** | **0/10** | **0/8** | **14/14** | **1/9** | **0/8** | 6/14 | **0.9981** |
| BALANCED_MIX_RESEARCH_CONTROL@BALANCED_MIX | 0/10 | 1/9 | 13/14 | 1/9 | 0/9 | 5/14 | 0.9749 |
| EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL@HIGHLIGHT_EXPLICIT | 0/10 | 3/10 | 12/14 | 2/9 | 0/10 | 4/14 | 0.9049 |

`NAIVE_EARLIEST_COMPATIBLE` and `BPM_KEY_ONLY_EARLY` are the only rows with nonzero `premature_exit_rate` and by far the worst `catastrophic/transitions` ratios (13/14 -- i.e. almost every transition either baseline makes is catastrophic under the new preservation metric). The recommended row is the only one with **zero** catastrophic transitions and the highest mean preservation ratio among all rows that actually capture opportunities. `BALANCED_MIX_RESEARCH_CONTROL` and `EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL` both show nonzero catastrophic rates -- expected and acceptable, since neither carries the default-mode catastrophic-ceiling acceptance criterion; they exist to demonstrate why they are not the default, not to meet it.

## 12. Planner output contract (for P0-M3-R3) -- superseded, see §17-21

The schema originally documented here (`beat_alignment_target`,
`downbeat_alignment_target`, `permitted_tempo_ratio`, `permitted_pitch_shift`,
a universal `next_track_entry_window_ms`) was found by PM REVIEW #2 to be
ambiguous and incomplete before any DSP pass could safely consume it. It has
been replaced; **§20 below is the current, authoritative schema.** This
section is kept only so the supersession is visible in-place; do not
implement against it.

## 13. Recommendation for P0-M3-R3

`SEAMLESS_FULL_TRACK_DEFAULT` should enter the next pass as the sole product-default policy. `BALANCED_MIX_RESEARCH_CONTROL` and `EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL` must remain research-only and are not authorized for any default or user-visible code path without a separate, explicit PM decision. `NAIVE_EARLIEST_COMPATIBLE`, `BPM_KEY_ONLY_EARLY`, `TAIL_ONLY_NATURAL_EXIT_BIASED`, and `FIXED_SECONDS_BEFORE_END_ONLY` are retained permanently as negative baselines/regression fixtures, never shipped. Pair compatibility (`policy/compatibility.py`) must gate `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` in the DSP-execution pass exactly as it does here -- timing eligibility and pair compatibility remain two independently-required gates, never merged into one score. As of PM REVIEW #2, `policy/boundary.py`'s complete-boundary planner (§17) is the canonical planner whenever an incoming track is modeled; `policy/policies.py`'s single-track `decide()` remains for fixtures where it is not.

This recommendation is a **research conclusion about policy/timing/compatibility**, not an authorization to begin DSP execution -- Signalsmith Stretch, Rubber Band, and the P1 engine remain out of scope and were not started (verified, §9 structural checks).

## 14. Unknowns / risks

- `NEAR_END_MAX_OVERLAP_MS = 40000`, the preservation floors, and the pair-compatibility thresholds (`0.12` stretch ceiling, `0.03` half/double-time tolerance) are P0 placeholders calibrated to make the 19 designed fixtures behave as intended and to sit inside the owner's own "20-40 seconds" example -- not derived from real-listener data or from any Apple disclosure. Real human-listening validation against `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §9's rubric remains a later-pass requirement.
- All 19 fixtures (14 timing + 5 pair) are metadata-only and hand-authored (`SYNTHETIC_EXACT`); no real-music validation occurred this pass.
- The genre-family compatibility map in `policy/compatibility.py` (`COMPATIBLE_GENRE_FAMILIES`) is a small, illustrative P0 taxonomy (4 families), not a production genre ontology -- a real implementation will need a much larger, likely provider-sourced, genre-compatibility model.
- How a real analyzer's actual confidence/error characteristics (BeatNet/CUE-DETR/All-In-One, per `docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md`) map onto the four discrete eligibility guards and the ten pair-compatibility components remains `UNKNOWN_NEEDS_RUNTIME_PROOF`.
- The `energy_continuity_hint`/`energy_continuity_priority` ranking signal is currently a coarse `STRONG`/`WEAK`/`UNKNOWN` tri-state authored directly on fixtures; a real analyzer-driven energy contour model is future work.

## 15. Files

- `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` (this document)
- `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md`
- `tools/p0m3/transition_policy/README.md`
- `tools/p0m3/transition_policy/fixtures/fixtures.json`
- `tools/p0m3/transition_policy/fixtures/pair_fixtures.json`
- `tools/p0m3/transition_policy/fixtures/manifest.json`
- `tools/p0m3/transition_policy/policy/metrics.py`
- `tools/p0m3/transition_policy/policy/compatibility.py`
- `tools/p0m3/transition_policy/policy/ranking.py`
- `tools/p0m3/transition_policy/policy/eligibility.py`
- `tools/p0m3/transition_policy/policy/policies.py`
- `tools/p0m3/transition_policy/policy/contract.py`
- `tools/p0m3/transition_policy/policy/__init__.py`
- `tools/p0m3/transition_policy/run_benchmark.py`
- `tools/p0m3/transition_policy/verify.py`
- `tools/p0m3/transition_policy/.gitignore`
- `tools/p0m3/transition_policy/results/*.json`, `results/SUMMARY.md`

## 16. PM review request

Please independently verify:

1. Run `python tools/p0m3/transition_policy/run_benchmark.py` and `python tools/p0m3/transition_policy/verify.py` and confirm `RESULT: ALL ASSERTIONS PASS`.
2. Open `results/decision_traces.json` and confirm TP-11's `SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT` decision selects `TP-11-C2` (near-end), never `TP-11-C1` (the ~2-minute trap), and that `TP-11-C1`'s own trace entry shows `outgoing_content_preservation_ratio < 0.90`.
3. Open `results/order_invariance.json` and confirm `order_invariant: true` with `TP-12-Y` as the winner under all three orderings.
4. Open `results/pair_compatibility.json` and confirm PAIR-02 (matching BPM, incompatible genre) shows `overall_dynamic_mix_eligible: false` and that the TP-11 integration row for PAIR-02 withholds `FULL_DJ_BLEND`.
5. Confirm no file under `tools/p0m3/transition_policy/` has a `.wav`/`.mp3`/other audio extension, and that `policy/*.py` contains no `rubberband`/`signalsmith` import.
6. Confirm `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md` still labels the owner observation `OWNER_SUBJECTIVE_REFERENCE` and that this document's §2 does not attribute any exact percentage/timing number to Apple.

---

# PM REVIEW #2 -- FINAL PRE-DSP CONTRACT REPAIR (2026-08-12)

PM REVIEW #2 identified three load-bearing gaps between the pass above (HEAD
`c440fd63a7d157cf34048e030f4eb382009e0800`) and a contract P0-M3-R3 could
safely render against without guessing: (R1) pair compatibility was applied
only AFTER an outgoing-exit-only ranking had already picked a winner; (R2)
incoming-entry planning was a hardcoded `next_track_entry_window_ms = {0,0}`
placeholder and `transition_onset_window_ms` spanned `onset..content_end`
rather than a real narrow window; (R3) `permitted_tempo_ratio` was populated
with a *deviation* value, not a literal ratio, and pitch had no explicit
unit/range contract; (R4) `overall_dynamic_mix_eligible` did not require
`structure_compatibility`/`intro_outro_texture_compatible` to be KNOWN, and
harmonic `UNKNOWN` passed the same hard gate as `COMPATIBLE`. Sections 17-21
document the repair. Everything in §1-16 above that PM REVIEW #2 did not
flag (near-end preservation model, catastrophic-reject guard, sensitivity
sweep, dead-air handling, highlight-intent gating) is unchanged.

## 17. R1 -- boundary-plan ranking (`policy/boundary.py`)

The prior pass's `decide()` ranked outgoing exit candidates using
`policy/eligibility.py` + `policy/ranking.rank_eligible_candidates`, then
called `build_transition_decision(..., pair=pair)` on the already-selected
winner. Pair compatibility could downgrade the winner's allowed transition
classes, but could never change *which* candidate won -- exactly the gap PM
REVIEW #2 R1 identified.

`policy/boundary.py`'s `plan_transition_boundary()` fixes this structurally,
in two phases:

1. **Safe-exit filter.** Every outgoing candidate is evaluated by the SAME
   `policy/eligibility.py` guards as before (structural evidence, confidence,
   vocal safety, preservation floor). Pair compatibility is never consulted
   in this phase -- this is what makes it structurally impossible for pair
   compatibility to authorize an early exit, not merely unlikely.
2. **Boundary cross-product + ranking.** For every (safe exit x incoming
   entry) combination, pair compatibility is evaluated AT that specific
   boundary (`_boundary_pair_compat`, using an optional per-boundary
   `boundary_overrides` map keyed by `"{exit_id}|{entry_id}"`, falling back
   to a track-level `pair_base`). All eligible boundaries are ranked by
   `policy/ranking.rank_boundary_plans`, whose key is: preservation ratio
   (2dp, safety-dominant) -> `eligible_for_dynamic_mix` (the pair-compatibility
   tier -- this is the new, load-bearing addition) -> combined structure
   score -> energy priority -> confidence -> a content-keyed tie-break. Pair
   compatibility now sits in tier 2, strictly above raw structure score
   (tier 3) -- so a pair-compatible boundary always outranks a pair-incompatible
   one at equal preservation, regardless of which outgoing candidate has the
   better raw structure score in isolation.

`TX-01` (`tools/p0m3/transition_policy/fixtures/transition_fixtures.json`)
is the required adversarial fixture: two safe near-end outgoing exits
(`TX01-OUT-A`, raw structure score 1.0; `TX01-OUT-B`, raw structure score
0.8) x two incoming entries. Every boundary touching `OUT-A` carries a
`HIGH` vocal-collision override (pair-incompatible); every boundary
touching `OUT-B` is fully compatible. The canonical planner selects
`OUT-B` + the stronger entry (`IN-2`) -- never `OUT-A`, despite `OUT-A`
having the higher raw outgoing-only structure score. Order invariance is
proven across BOTH the outgoing-exit array and the incoming-entry array
independently and jointly (normal, each-reversed, both-reversed, and two
independently-seeded shuffles) -- see `results/boundary_planning.json`'s
`tx01_order_invariance` (`order_invariant: true`) and `verify.py`'s R1/R2
section (checks 1-4).

The full cross-product is preserved in `candidate_rank_trace` for every
combination, not only the winner (`boundary_rank`, `selected`,
`selection_reason_codes` on every entry) -- TX-01 has exactly 2 exits x 2
entries = 4 trace entries, one marked `selected: true`.

## 18. R2 -- incoming entry planning + real onset windows

`policy/boundary.py` plans a genuine incoming-entry candidate instead of a
hardcoded `{0, 0}`. An entry candidate is eligible only if:

- `t_ms == 0` (always valid -- starting at the top of the track never
  removes anything), OR
- it is flagged `is_authored_silence_skip` AND falls within the track's
  `leading_silence_ms` (only consulted when `leading_silence_is_authored_non_musical: true`), OR
- it carries explicit `phrase_section_evidence` or `cue_evidence`.

Any other later-than-zero candidate is rejected
(`ENTRY_SKIPS_MEANINGFUL_INTRO_WITHOUT_EVIDENCE`) -- it would silently
remove real intro content. `incoming_effective_content_start_ms` mirrors
the outgoing side's `effective_content_end_ms` dead-air handling exactly
(only trims when explicitly authored as non-musical).

Four fixtures cover the required cases:

| Fixture | Case | Result |
|---|---|---|
| TX-02 | 0ms is genuinely correct | Selects `t=0`; a later no-evidence candidate is rejected |
| TX-03 | authored leading silence (5000ms) | Selects the silence-skip entry at exactly 5000ms (not 0ms, not the too-far 15000ms candidate, which is rejected) |
| TX-04 | later phrase/cue clearly better | Selects the phrase-evidenced entry at 8000ms over 0ms |
| TX-05 | entry choice changes compatibility | Selects the entry whose boundary is pair-compatible, rejecting the otherwise-identical entry that triggers a vocal-collision override |

`transition_onset_window_ms` (outgoing side) and the incoming entry window
are both now real narrow windows: `t_start_ms == t_end_ms` for an exact cue
timestamp, or an explicit authored `onset_window_ms: [start, end]` region
when a candidate carries one -- never `onset..effective_content_end_ms`.
This applies to both the new boundary builder and the legacy single-track
builder (`build_transition_decision`) alike.

## 19. R3 -- unambiguous tempo/pitch contract

`policy/compatibility.py`'s `PairCompatibilityResult` now separates:

- `required_tempo_stretch_pct` (retained, unchanged meaning: how far the
  matched relation's deviation is from a clean match)
- `required_tempo_ratio` (**new**): the literal playback-rate ratio
  (`bpm_out / bpm_in`) needed to align the incoming track's tempo grid to
  the outgoing track's. For a legitimate `HALF_DOUBLE` relation this is
  reported as `1.0` with `tempo_requires_playback_rate_change: False`,
  because a half/double-time pair needs only a downbeat/bar-grid
  reinterpretation, not an actual speed change.
- `tempo_requires_playback_rate_change` (**new**): `True` for `DIRECT`/
  `EXCESSIVE_STRETCH`, `False` for `HALF_DOUBLE`.

`policy/contract.py`'s `PlannerDecision` no longer has a field named
`permitted_tempo_ratio` populated with a deviation value. It has:

- `required_tempo_ratio` (copied from the pair-compatibility result)
- `permitted_tempo_ratio_max_deviation` (the `0.12` ceiling -- explicitly
  named as a deviation, sourced from a single constant,
  `policy/compatibility.MAX_JUSTIFIED_TEMPO_STRETCH_PCT`, shared by both
  the gating logic and the contract so they can never drift apart)
- `required_pitch_shift_semitones` (0 when harmonic is COMPATIBLE, else
  `None` -- this project does not compute a real semitone value without
  actual key detection, and does not fabricate one)
- `permitted_pitch_shift_semitones_min` / `_max` (`-3`/`3`, an explicit
  symmetric range, replacing the old bare `permitted_pitch_shift = 3`)

All four are populated only when `FULL_DJ_BLEND` is actually in the
allowed class set (never unconditionally).

## 20. R4 -- strict FULL_DJ_BLEND hard-gate contract (current, authoritative)

`policy/compatibility.py`'s `overall_dynamic_mix_eligible` hard gate now
requires ALL of: genre compatible, tempo within the permitted relation,
beat confidence HIGH, downbeat confidence HIGH, **structure_compatibility
KNOWN and COMPATIBLE** (not merely non-blocking/UNKNOWN -- new), **intro/
outro texture KNOWN and COMPATIBLE** (new), vocal-safety, bass/percussion-
safety, analysis confidence HIGH, and harmonic COMPATIBLE **or** UNKNOWN
with an explicit `harmonic_not_load_bearing_reason` exception (new).
Energy continuity remains a ranking/preference signal that participates
only after these hard gates (`policy/ranking.py` tier 3+), never a hard
rejection by itself -- a `WEAK`-energy but otherwise fully compatible pair
(`PAIR-01`) is still `FULL_DJ_BLEND`-eligible.

Five mutation pair fixtures (`PAIR-06..10`) prove the tightened gate is
real, not merely documented:

| Pair | Mutation | Result |
|---|---|---|
| PAIR-06 | `structure_compatibility` omitted (UNKNOWN) | NOT eligible -- UNKNOWN never equals known COMPATIBLE |
| PAIR-07 | `intro_outro_texture_compatible: false` (UNKNOWN) | NOT eligible -- same principle |
| PAIR-08 | `harmonic_relationship` omitted, no exception | NOT eligible -- downgraded, not silently COMPATIBLE |
| PAIR-09 | `harmonic_relationship` omitted, WITH an explicit narrow `harmonic_not_load_bearing_reason` | Eligible -- the exception path is real, narrow, and testable |
| PAIR-10 | `harmonic_relationship: "INCOMPATIBLE"` plus an exception reason present | NOT eligible -- the exception only ever applies to UNKNOWN, never overrides a known INCOMPATIBLE |

### 20.1 Current, authoritative `PlannerDecision` schema (supersedes §12)

```json
{
  "fixture_id": "string",
  "listener_intent": "SEAMLESS_FULL_TRACK_DEFAULT | BALANCED_MIX | HIGHLIGHT_EXPLICIT",
  "policy_name": "string",
  "decision_type": "TRANSITION | PLAY_THROUGH | NO_SPECIAL_TRANSITION",

  "current_track_effective_content_end_ms": "int | null",
  "selected_outgoing_exit_candidate_id": "string | null",
  "transition_onset_window_ms": {"t_start_ms": "int", "t_end_ms": "int"},
  "outgoing_last_audible_target_ms": "int | null",
  "outgoing_content_preservation_target": "float | null",

  "selected_incoming_entry_candidate_id": "string | null",
  "incoming_effective_content_start_ms": "int | null",
  "next_track_entry_window_ms": "{t_start_ms, t_end_ms} | null (null ONLY when no incoming track was modeled for this fixture)",
  "incoming_entry_reason_codes": ["string", "..."],
  "incoming_phrase_section_evidence": "bool | null",

  "allowed_transition_class_set": ["FULL_DJ_BLEND | SHORT_EQ_BLEND | SIMPLE_CROSSFADE | GAPLESS | CUT | NO_SPECIAL_TRANSITION", "..."],
  "pair_compatibility_components": "object | null (null only when no pair was supplied/computed)",

  "outgoing_beat_alignment_target_ms": "int | null",
  "incoming_beat_alignment_target_ms": "int | null",
  "outgoing_downbeat_alignment_target_ms": "int | null",
  "incoming_downbeat_alignment_target_ms": "int | null",
  "beat_phase_relation": "ALIGNED | OFFSET | UNKNOWN | NOT_APPLICABLE",
  "bar_phase_relation": "ALIGNED | OFFSET | UNKNOWN | NOT_APPLICABLE",

  "required_tempo_ratio": "float | null",
  "permitted_tempo_ratio_max_deviation": "float | null (a DEVIATION ceiling, e.g. 0.12 -- never a literal ratio)",
  "required_pitch_shift_semitones": "int | null",
  "permitted_pitch_shift_semitones_min": "int | null",
  "permitted_pitch_shift_semitones_max": "int | null",

  "energy_continuity_target": "string",
  "vocal_collision_constraints": "string",
  "bass_collision_constraints": "string",
  "analysis_confidence": "NONE | LOW | MEDIUM | HIGH",
  "reason_codes": ["string", "..."],
  "queue_order_independent_of_exit_timing": true,
  "candidate_rank_trace": ["... every evaluated (exit,entry) boundary or candidate, with boundary_rank/eligible_rank + selected + selection_reason_codes, see results/decision_traces.json and results/boundary_planning.json ..."]
}
```

Legacy single-track decisions (fixtures with no incoming track modeled, letters A-N) use the SAME schema; `selected_incoming_entry_candidate_id`, `incoming_effective_content_start_ms`, and `next_track_entry_window_ms` are honestly `None` (never a fabricated `{0,0}`) with `incoming_entry_reason_codes: ["INCOMING_ENTRY_NOT_MODELED_FOR_THIS_FIXTURE"]`.

## 21. Updated verification + PM REVIEW #2 closeout

```
python tools/p0m3/transition_policy/run_benchmark.py
python tools/p0m3/transition_policy/verify.py
```

**111 of 111 assertions PASS** (up from the prior pass's 66 -- all 66 are
retained and re-verified under the corrected schema; 45 new checks cover
PM REVIEW #2's R1-R4 plus the 17 explicit stop-conditions from that
comment). New result files: `results/boundary_planning.json` (TX-01..05
full decisions + TX-01 order-invariance proof) and
`results/mutation_pair_report.json` (PAIR-06..10). `results/pair_compatibility.json`
and `results/SUMMARY.md` now cover all 10 pair fixtures.

Do not start Signalsmith, Rubber Band, audio rendering, P0-M3-R3, or P1 --
none were started in this repair pass.

---

# PM REVIEW #3 -- TRUE FINAL DSP-SAFETY REPAIR (2026-08-12)

PM REVIEW #3 independently mutation-tested HEAD `06eab3d342b2e0ac85a57eb65e11331ef817ed6d` and found four load-bearing DSP-handoff defects the prior 111 assertions did not cover: (R5) `FULL_DJ_BLEND` could be offered when the selected boundary's incoming candidate had NO beat/downbeat evidence at all (pair-level *confidence* was checked, not the actual selected candidates); (R6) the tempo-compatibility gate and the emitted `required_tempo_ratio` used two different denominators and could disagree (100/88 BPM: gate said DIRECT-eligible, ratio's own deviation exceeded the stated ceiling); (R7) `harmonic_not_load_bearing_reason` accepted any non-empty string, making the harmonic-UNKNOWN exception an arbitrary free-text bypass; (R8) boundary ranking used the raw rounded preservation ratio as its primary key even after the hard safety floor had already filtered candidates, so a 1.00-but-incompatible boundary could beat a 0.99-but-compatible one purely on a marginal preservation edge; (R9) `beat_phase_relation`/`bar_phase_relation` were fabricated as `"ALIGNED"` from `eligible_for_dynamic_mix`, not derived from any real measurement. Sections 22-26 document the repair. The accepted preservation model, catastrophic-reject guard, near-end selection, dead-air handling, incoming-entry planning, complete boundary traces, order invariance, and highlight-never-default behavior are all unchanged.

## 22. R5 -- boundary-specific beat/downbeat alignability

`policy/compatibility.py`'s `beat_compatibility`/`downbeat_compatibility` gate is analyzer-*confidence*-based and pair-level -- it says nothing about whether the SPECIFIC exit/entry candidates a boundary actually selects carry renderable alignment targets. `policy/boundary.py` now adds a second, boundary-local check: `boundary_beat_downbeat_alignable = exit_candidate.beat_downbeat_aligned AND entry_candidate.beat_downbeat_aligned`. When false, `FULL_DJ_BLEND` is stripped from `allowed_transition_class_set` regardless of what pair-level compatibility says (reason code `FULL_DJ_BLEND_WITHHELD_NO_BOUNDARY_ALIGNMENT_EVIDENCE`); `0ms`/any other candidate remains fully valid for `SIMPLE_CROSSFADE`/`SHORT_EQ_BLEND`/other non-DJ classes.

Two required fixtures prove both directions:

- **TX-02 (case A)**: incoming entry at `0ms` with no beat/downbeat evidence. `allowed_transition_class_set = ['SHORT_EQ_BLEND', 'SIMPLE_CROSSFADE']` -- `FULL_DJ_BLEND` withheld, `incoming_beat_alignment_target_ms = null`.
- **TX-06 (case B)**: incoming entry at `0ms`, but explicitly authored `beat_downbeat_aligned: true` (a genuine beat/downbeat anchor at the very start of the track). `allowed_transition_class_set = ['FULL_DJ_BLEND', 'SHORT_EQ_BLEND', 'SIMPLE_CROSSFADE']`, `incoming_beat_alignment_target_ms = 0`.

A single `beat_downbeat_aligned` boolean per candidate is used as the explicit machine-readable evidence for BOTH the beat and downbeat/bar target on that side (contract.py sets both target fields from it) -- this project judged a full split into four independent boolean fields unnecessary scope for this repair (the closeout boundary explicitly asks for a narrow fix), since the combined boolean already gives distinct, real per-candidate evidence on both the exit and entry side, which is what was actually missing.

## 23. R6 -- one canonical tempo-ratio definition

`policy/compatibility._tempo_relation` now computes, for each candidate octave multiplier `m` in `{1.0 (direct), 2.0, 0.5}`: `ratio = bpm_out / (bpm_in * m)`, `deviation = abs(ratio - 1.0)`. The SAME `ratio`/`deviation` pair is used for BOTH the classification gate (`deviation <= MAX_JUSTIFIED_TEMPO_STRETCH_PCT` for DIRECT, `<= HALF_DOUBLE_TIME_TOLERANCE_PCT` for the best-fitting octave) and the emitted `required_tempo_ratio`/`required_tempo_stretch_pct` -- they can no longer mathematically disagree.

PM's required mutation, before/after:

| BPM pair | Field | Before | After |
|---|---|---|---|
| out=100, in=88 | `tempo_compatibility` | `DIRECT` | `EXCESSIVE_STRETCH` |
| | `required_tempo_ratio` | `1.1364` | `1.1364` |
| | `abs(ratio-1)` vs `0.12` ceiling | `0.1364 > 0.12` **while marked eligible** | `0.1364 > 0.12`, correctly **not** DIRECT |
| | `overall_dynamic_mix_eligible` | `True` (bug) | `False` |

Symmetric check: out=88, in=100 -> `ratio = 88/100 = 0.88`, `deviation = 0.12` (at the ceiling) -> `DIRECT`, eligible. Both directions use the identical `bpm_out/bpm_in` formula -- there is no directional special case.

Non-exact HALF_DOUBLE residual, PM's required mutation:

| BPM pair | Field | Before | After |
|---|---|---|---|
| out=120, in=61.8 | `tempo_compatibility` | `HALF_DOUBLE` | `HALF_DOUBLE` (unchanged -- classification was already correct) |
| | `required_tempo_ratio` | `1.0` (bug: claimed no correction) | `0.9709` (real residual) |
| | `tempo_requires_playback_rate_change` | `False` (bug) | `True` |

An exact half/double pair (out=120, in=60) still correctly reports `required_tempo_ratio=1.0`, `tempo_requires_playback_rate_change=False` -- the fix only removes the FALSE claim for non-exact relations, it doesn't add unnecessary correction to genuinely exact ones.

## 24. R7 -- structured, machine-verifiable harmonic exception

The harmonic-UNKNOWN exception no longer reads `harmonic_not_load_bearing_reason` at all. It requires, simultaneously:

- `harmonic_exception_kind` in `{NON_TONAL_RHYTHMIC, PERCUSSION_ONLY, NOISE_TEXTURE}` (an enum, not free text)
- `tonal_content_class == "NON_TONAL"`
- `tonal_analysis_confidence == "HIGH"`

PM's required mutation (`harmonic_not_load_bearing_reason = "x"` on an otherwise fully-compatible pair) now yields `overall_dynamic_mix_eligible = False`, `harmonic_exception_applied = False` -- the field is inert. Four pair fixtures cover the full decision surface: `PAIR-09` (all three structured fields valid -> eligible), `PAIR-11` (old free-text field, now inert -> rejected), `PAIR-12` (valid kind+class but `tonal_analysis_confidence=LOW` -> rejected), `PAIR-13` (unrecognized `harmonic_exception_kind` -> rejected).

Pitch determinism: when the exception applies, `required_pitch_shift_semitones = 0` and `permitted_pitch_shift_semitones_min/max = 0/0` (a zero-width envelope -- there is no tonal basis to justify any correction range). When harmonic is genuinely `COMPATIBLE`, the normal `required=0`, range `-3..3` envelope applies. `FULL_DJ_BLEND` is withheld entirely (and pitch is simply unused/null) for every other harmonic state -- there is never a case where `required_pitch_shift_semitones` is `null` alongside a nonzero permitted range.

## 25. R8 -- ranking within preservation safety bands

`policy/metrics.preservation_band(ratio, floor)` returns `PREFERRED` (`>=0.97`), `ACCEPTABLE` (`>=floor, <0.97`), or `UNSAFE` (`<floor`) -- computed once, at eligibility time, against whichever floor was actually applied. `policy/ranking.py`'s sort key now leads with this band, THEN pair compatibility, THEN structure/energy/confidence, THEN the exact preservation ratio as a fine-grained tie-break, THEN the deterministic ID tie-break -- exactly the 7-level order PM specified. `UNSAFE` candidates never reach the ranker at all (they're excluded by the existing hard eligibility-floor guard before ranking begins), so this is a re-ordering of already-safe candidates, not a weakening of the floor.

`TX-07` is the required regression fixture: `OUT-A` (preservation exactly `1.00`, pair-incompatible via a `HIGH` vocal-collision override) vs `OUT-B` (preservation exactly `0.99`, pair-compatible), both in the `PREFERRED` band. Winner: **`OUT-B`** -- `outgoing_content_preservation_target = 0.99`, `allowed_transition_class_set` includes `FULL_DJ_BLEND`. `OUT-A` remains fully present in `candidate_rank_trace` (evaluated, not silently dropped), just outranked. The same fixture also carries `OUT-C` (preservation `0.94`, pair-compatible) and `OUT-D` (preservation `0.85`, pair-compatible): both are proven to never appear in `candidate_rank_trace` at all -- `OUT-C` is rejected via `BELOW_PRESERVATION_FLOOR`, `OUT-D` additionally via `CATASTROPHIC_PRESERVATION_LOSS` -- direct evidence that compatibility can never rescue a candidate across the hard floor, regardless of how compatible the pair is. Order invariance re-verified under reversed and independently-shuffled outgoing-candidate arrays.

## 26. R9 -- honest phase semantics, explicit render-plan actions

`beat_phase_relation`/`bar_phase_relation` are OBSERVED-relation fields. This P0 prototype has no beat-index/bar-position metadata anywhere to derive a real measured phase relation from, so as of this repair they can only ever report `NOT_MEASURED` (both-side targets are known, but no real phase computation exists) or `NOT_APPLICABLE` (a target is missing on one/both sides) -- **never `ALIGNED`**, which the prior pass fabricated directly from `eligible_for_dynamic_mix`.

Two new fields carry the actual DSP-renderer instruction, structurally separate from the (never-fabricated) observed fields: `beat_alignment_action = "ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET"` and `bar_alignment_action = "ALIGN_OUTGOING_DOWNBEAT_TARGET_TO_INCOMING_DOWNBEAT_TARGET"` whenever both respective targets are known, else `"NOT_APPLICABLE"`. Example (TX-01 winner): `beat_phase_relation="NOT_MEASURED"`, `beat_alignment_action="ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET"` -- the contract now honestly says "I know both targets and here is the action to take" without ever claiming a phase relationship that was never measured.

## 27. Updated verification + PM REVIEW #3 closeout

```
python tools/p0m3/transition_policy/run_benchmark.py
python tools/p0m3/transition_policy/verify.py
```

**151 of 151 assertions PASS** (up from PM REVIEW #2's 111 -- all 111 retained and re-verified, with 2 assertions updated for legitimate schema/behavior changes: the pair/transition fixture-count checks now reflect 13/7 fixtures, and TX-01's `beat_phase_relation` check now expects the honest `NOT_MEASURED` value instead of the retired `ALIGNED`/`OFFSET` enum. 40 new checks cover R5-R9 plus PM REVIEW #3's 18 explicit stop-conditions). New/updated fixtures: `TX-06`, `TX-07` (transition_fixtures.json, now 7 total), `PAIR-11`, `PAIR-12`, `PAIR-13` (pair_fixtures.json, now 13 total; `PAIR-09` updated to the structured exception schema).

Do not start Signalsmith, Rubber Band, audio rendering, P0-M3-R3, or P1 -- none were started in this repair pass.
