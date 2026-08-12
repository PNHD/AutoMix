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

## 12. Planner output contract (for P0-M3-R3)

`tools/p0m3/transition_policy/policy/contract.py`'s `PlannerDecision`:

```json
{
  "fixture_id": "string",
  "listener_intent": "SEAMLESS_FULL_TRACK_DEFAULT | BALANCED_MIX | HIGHLIGHT_EXPLICIT",
  "policy_name": "string",
  "decision_type": "TRANSITION | PLAY_THROUGH | NO_SPECIAL_TRANSITION",
  "current_track_effective_content_end_ms": "int | null",
  "transition_onset_window_ms": {"t_start_ms": "int", "t_end_ms": "int"},
  "outgoing_last_audible_target_ms": "int | null",
  "outgoing_content_preservation_target": "float | null",
  "next_track_entry_window_ms": {"t_start_ms": "int", "t_end_ms": "int"},
  "allowed_transition_class_set": ["FULL_DJ_BLEND | SHORT_EQ_BLEND | SIMPLE_CROSSFADE | GAPLESS | CUT | NO_SPECIAL_TRANSITION", "..."],
  "pair_compatibility_components": "object | null (null only when no pair was supplied)",
  "beat_alignment_target": "int | null",
  "downbeat_alignment_target": "int | null",
  "permitted_tempo_ratio": "float | null",
  "permitted_pitch_shift": "int | null",
  "energy_continuity_target": "string",
  "vocal_collision_constraints": "string",
  "bass_collision_constraints": "string",
  "analysis_confidence": "NONE | LOW | MEDIUM | HIGH",
  "reason_codes": ["string", "..."],
  "queue_order_independent_of_exit_timing": true,
  "candidate_rank_trace": ["... full per-candidate trace incl. eligible_rank, see results/decision_traces.json ..."]
}
```

`allowed_transition_class_set` reuses `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1's taxonomy exactly. `permitted_tempo_ratio`/`permitted_pitch_shift` reuse the `0.12`/`3-semitone` envelope from the prior pass and are only ever populated when `FULL_DJ_BLEND` is actually in the allowed set (never unconditionally).

## 13. Recommendation for P0-M3-R3

`SEAMLESS_FULL_TRACK_DEFAULT` should enter the next pass as the sole product-default policy. `BALANCED_MIX_RESEARCH_CONTROL` and `EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL` must remain research-only and are not authorized for any default or user-visible code path without a separate, explicit PM decision. `NAIVE_EARLIEST_COMPATIBLE`, `BPM_KEY_ONLY_EARLY`, `TAIL_ONLY_NATURAL_EXIT_BIASED`, and `FIXED_SECONDS_BEFORE_END_ONLY` are retained permanently as negative baselines/regression fixtures, never shipped. Pair compatibility (`policy/compatibility.py`) must gate `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` in the DSP-execution pass exactly as it does here -- timing eligibility and pair compatibility remain two independently-required gates, never merged into one score.

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
