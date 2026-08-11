# P0-M2-R1 — AutoMix Quality Benchmark Contract

Status date: 2026-08-11 (PM REVIEW #2 — narrow repair pass)

## 0. Execution profile actually used

- **Execution agent:** Claude Code (Claude Agent SDK CLI), continuing the same session that produced commits `0d7ba89` (initial pass) and `d3c9f8b` (first repair pass, R1–R9).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High (owner/PM Desktop-UI attestation, not independently introspectable — explicitly not a stop condition per Issue #4 and both prior PM reviews).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **This revision addresses** the PM's `PM REVIEW #2 — NARROW REPAIR REQUIRED` comment on Issue #4 (posted 2026-08-11T03:45:27Z), repair items R10–R12. R1, R3, R4, R6, R7, R8, R9 from the first repair pass were confirmed materially improved by this review and are **not** re-litigated here except where R10–R12 required a downstream edit to text they touch (e.g. the P0→P1 gate's corpus-minimums block, which R1–R9 already introduced and R10 now extends).

## 1. Result

**PASS**

Every Issue #4 acceptance criterion remains satisfied (§15). This revision closes the two remaining load-bearing specification defects the PM's second review identified (R10: holdout sample-size semantics for `G3`/`G4`, and the `G1` tie/decisive-count arithmetic; R11: the missing binding transition-class taxonomy) plus one anticipatory fix requested before P0-M3 ever consumes this contract (R12: re-auditing all 10 `rejected` catalog entries against that taxonomy, since several were grounded in "the benchmark cannot currently measure this" rather than genuine musical/structural impossibility — an evaluation-capability gap, not proof of impossibility, per the PM's explicit correction).

## 2. Purpose

Define the benchmark contract that decides whether AutoMix is musically better than naive crossfade / BPM-key-only mixing, and whether P1 (local AutoMix engine implementation) is allowed to start. This document, its companion manifest schema (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`), and the optional pair catalog (`docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`) together are the full P0-M2-R1 deliverable set. No AutoMix engine code, no audio files are included. P0-M3 may build disposable, non-production benchmark-execution prototypes needed to actually run this contract and produce measurements (this is the mechanism by which the P1 gate in §12 is ever evaluated at all); only the shipping, production, multi-platform AutoMix engine is blocked pending the gate.

## 3. Core benchmark principle

**BPM/key compatibility is never sufficient evidence of AutoMix quality.**

`docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §8–§10 independently demonstrates why: the pinned SimpMusic baseline is `TEMPO_AWARE` and has working Camelot key-compatibility scoring, yet has zero beat-timestamp, downbeat, phrase, section, or content-activity awareness, and its incoming-track start position is unconditionally `0` regardless of the outgoing track's phase. A benchmark that only checked "did BPM/key roughly match" would score SimpMusic as if the transition-planning problem were solved. It is not. This benchmark must therefore detect failures in cue-point choice, beat phase, downbeat/bar alignment, phrase alignment, section-aware entry/exit, vocal collision, bass/percussion masking, energy trajectory, short-term loudness continuity, tempo-stretch artifacts, pitch-shift artifacts, clicks/pops/discontinuities, transition-style appropriateness, and confidence/fallback behavior.

A good engine must be able to decide that a complex DJ blend is the wrong transition for a given pair. This benchmark scores that decision explicitly (Lane E, §4.5). **Symmetrically, the benchmark must not punish an engine for correctly deciding a complex DJ blend *is* the right transition for a pair that only looks adversarial on paper, and must not confuse "this benchmark currently lacks a way to measure success objectively" with "success here is impossible"** — the latter distinction is the specific subject of this revision (R12, §6, §10).

### 3.1 Terminology gate (binding, per `.agents/skills/automix-forensic-research/SKILL.md`)

| Term | Meaning | Not satisfied by |
|---|---|---|
| Tempo/BPM-aware | scalar or estimated tempo used | — |
| Beat-aware | explicit beat timestamps/grid used | a derived `60000/BPM` theoretical grid |
| Downbeat-aware | bar starts/downbeats identified and used | beat-awareness alone |
| Phrase-aware | transition entry/exit uses phrase boundaries | downbeat-awareness alone, or a fixed "every 32 beats" proxy |
| Section-aware | intro/verse/chorus/outro or equivalent structural sections identified and used | phrase-awareness alone |

Every benchmark report produced under this contract must classify the system under test against this table explicitly, using the same eight-level scheme P0-M1 §8 used for SimpMusic.

## 4. Benchmark lanes

Each lane is scored independently; a single aggregate score is explicitly disallowed. Every case type below must have at least one corresponding fixture/pair in the manifest; concrete representative pairs are enumerated in `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`.

### 4.1 Lane A — Timing / structure

Same BPM but wrong beat phase · beat-aligned but wrong downbeat/bar phase · same BPM/key but incompatible phrase timing · intro/outro opportunities · chorus/drop/build-up boundaries · pickup/anacrusis starts · long silence/non-musical tails · tracks without clean intro/outro · variable tempo where feasible · non-4/4 or ambiguous meter where feasible.

"Adversarial" here describes the *input*, not the required *output*. A system that measurably corrects the mismatch before executing a full blend is scored as having succeeded, not as having chosen the wrong class (§6). Where the benchmark has no defined objective condition for a specific kind of correction (e.g. cross-meter downbeat compatibility, `PAIR-SYN-A-010`), the pair routes to mandatory human confirmation rather than categorical rejection (§6, §10).

### 4.2 Lane B — Content collision

vocal→vocal · sustained vocal outro→vocal intro · dense bass→dense bass · percussion-heavy overlap · instrumental→vocal · sparse→dense · dense→sparse.

The vocal/bass-overlap objective metrics (§8) are computed against the **rendered, post-mix** transition audio, not naively against source-fixture activity annotations — a system that applies genuine stem/vocal attenuation during the overlap is scored on the resulting audible collision, not disqualified merely because the untouched source fixtures overlap (R12).

### 4.3 Lane C — Energy / loudness

high→high · low→high · high→low · gradual buildup/drop · large mastering-loudness differences · locally quiet transition region despite high integrated loudness. Loudness terminology is binding: `momentary` = 400 ms, `short-term` = 3 s, `integrated` = programme/start-stop-style gated measurement, all via ITU-R BS.1770-5 with EBU R128/Tech 3341 window-naming.

### 4.4 Lane D — Harmonic / tempo

compatible key + close tempo · compatible key + large tempo gap · incompatible key + close tempo · half/double-time cases · pitch shifting helps · pitch shifting should be avoided · stretch within reasonable range · stretch outside reasonable range. Per-pair `manipulation_constraints` define "safe correction range" concretely (§6, §10).

### 4.5 Lane E — Confidence / fallback

Corpus must contain pairs where the expected preferred behavior is `FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, `SIMPLE_CROSSFADE`, `GAPLESS`, `CUT`, or `NO_SPECIAL_TRANSITION` (§5 defines each operationally). This lane scores whether the **chosen transition class** was appropriate, not only whether DSP execution was smooth. Lane E carries a dedicated internal subset — pairs whose `transition_class_policy.rejected` categorically excludes `FULL_DJ_BLEND` for a real, fixture-authored reason — used by the `C11`/`G4` zero-tolerance check (§10, §12).

## 5. Transition-Class Taxonomy (new — R11)

**Binding, operational definitions.** These labels are load-bearing in `transition_class_policy`, `C11`, and `G4`. A candidate engine's self-reported label for its own transition is recorded for diagnostics only and is **never** authoritative for any gate — the benchmark runner assigns `observed_class` from measured, rendered-output behavior via the deterministic decision procedure in §5.2, using the transition render record fields defined in `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §10.

### 5.1 Class definitions

| Class | Overlap expectation | Beat/downbeat sync — class contract? | Duration semantics | Automation permitted | Cue-point selection | Stem-separation |
|---|---|---|---|---|---|---|
| `GAPLESS` | Zero (instant, sample-accurate join) | N/A — no overlap window exists to synchronize | The "transition" itself is 0 ms by definition; not a tunable parameter | None — any detected volume/EQ/tempo/pitch automation at the join disqualifies this label | N/A — outgoing plays to its own authored end, incoming starts at its own authored beginning, no search | Not applicable to this class |
| `NO_SPECIAL_TRANSITION` | Zero, same as `GAPLESS` | N/A | Same as `GAPLESS` | None | N/A — same natural-boundary behavior as `GAPLESS` | Not applicable |
| `CUT` | Zero | N/A | Same as `GAPLESS`/`NO_SPECIAL_TRANSITION` at the waveform level | None | **Yes** — this is what distinguishes `CUT` from the two classes above: the engine chose a non-natural boundary (truncated the outgoing track before its authored end, or started the incoming track at other than its authored beginning) | Not applicable |
| `SIMPLE_CROSSFADE` | Nonzero | Not required | Not hardcoded to a specific algorithm; typically short-to-moderate, but classification never depends on a duration number | Volume/gain automation only — no EQ/filter automation, no tempo/pitch automation | Yes | If applied, reported as a modifier (§5.3), does not change the base class |
| `SHORT_EQ_BLEND` | Nonzero | Not required (any beat-alignment quality achieved is scored via §8/§9 metrics, not required for the label) | Not hardcoded; typically shorter than a full blend, but classification never depends on duration alone | Volume/gain **and** EQ/filter automation; no tempo/pitch automation | Yes | Modifier, does not change base class |
| `FULL_DJ_BLEND` | Nonzero | **Contractual expectation, not a classification gate**: this label requires tempo/pitch automation to be present (with or without EQ automation) — see §5.2 rule 3f/3g. Whether the resulting beat/downbeat alignment is actually *good* is scored separately via `COND_BEAT_OK`/`COND_DOWNBEAT_OK`/`C1`/`C2` (§7, §10); a badly-aligned but tempo/pitch-processed blend is still classified `FULL_DJ_BLEND` and then fails on execution-quality grounds, not on class-assignment grounds | Not hardcoded; typically the longest of the processed classes, but classification never depends on duration alone | Volume/gain, EQ/filter, and tempo/pitch automation all may be present; tempo/pitch automation presence is the primary distinguishing signal from `SHORT_EQ_BLEND` | Yes, and expected (deliberate entry/exit region choice) | Modifier, does not change base class |

Duration is deliberately **not** used anywhere above as a hard classification threshold, per R11's "typical/allowed duration semantics without hardcoding one algorithm" instruction — a class is identified by *what kind of processing was rendered*, not by *how long it lasted*. This also directly serves R12: nothing in this taxonomy requires tempo *matching* for the `FULL_DJ_BLEND` label, only tempo/pitch automation's *presence* — closing the D-008 gap the PM identified (a 60% tempo gap does not make the *label* `FULL_DJ_BLEND` inapplicable; it makes the *quality condition* `COND_TEMPO_ENVELOPE_OK` hard to satisfy, which is scored separately, see the D-008 re-audit in the pair catalog).

### 5.2 Classification decision procedure (deterministic, runner-applied)

Given a transition render record (schema §10) for a rendered pair:

1. Measure `overlap_ms`.
2. **If `overlap_ms` ≤ a small measurement-noise epsilon (default 20 ms, treated as zero):**
   a. Measure `outgoing_used_natural_full_duration` and `incoming_used_natural_start` against the fixtures' own `authored_exit_boundary_ms`/`authored_entry_boundary_ms` (schema §3).
   b. If both are `true` **and** the pair's `is_continuous_work` = `true` → `observed_class = GAPLESS`.
   c. Else if both are `true` **and** `is_continuous_work` = `false` → `observed_class = NO_SPECIAL_TRANSITION`.
   d. Else (either boundary was not natural — a truncation or non-natural start occurred) → `observed_class = CUT`.
3. **If `overlap_ms` > the epsilon:**
   a. If `has_volume_automation = false` → `observed_class = UNCLASSIFIED_ANOMALY` (overlap present with no detected processing at all is not a valid rendering of any of the six classes; flagged for manual review, never silently mapped).
   b. Else if `has_eq_automation = false` and `has_tempo_pitch_automation = false` → `observed_class = SIMPLE_CROSSFADE`.
   c. Else if `has_tempo_pitch_automation = false` (EQ automation present, no tempo/pitch) → `observed_class = SHORT_EQ_BLEND`.
   d. Else (`has_tempo_pitch_automation = true`, with or without EQ automation) → `observed_class = FULL_DJ_BLEND`.
4. Set `class_label_mismatch = (engine_reported_class != observed_class)` for diagnostic reporting. This field has no gate consequence on its own — it is a signal about engine self-assessment honesty, never a scoring input.

This procedure uses **only** measured render-time signals (steps 2a/3a–d) plus static, pre-authored fixture/pair annotations that are fully known at corpus-design time (`authored_*_boundary_ms`, `is_continuous_work`) — never the engine's own `engine_reported_class`. This is the direct answer to R11's "the benchmark, not the candidate engine, must own class assignment for gate purposes," and to REQUIRED VALIDATION item 5 ("confirm no candidate engine can pass `G4` merely by self-reporting a class label inconsistent with the rendered output"): `G4` and `C11` are always evaluated against `observed_class`, and `engine_reported_class` is not a scoring input anywhere in this contract.

### 5.3 Stem/source-separation as a modifier, not a class

Whether a system applies stem/source-separation or targeted vocal/instrument attenuation during the overlap is recorded as the boolean `stem_separation_applied` (schema §10) and never determines the base class from §5.2 — it is an orthogonal modifier. It matters in exactly two places in this contract: (1) the vocal/bass-overlap objective metrics are computed against the rendered, post-attenuation audio regardless of whether this modifier is set (§8), and (2) a small number of `transition_class_policy.accepted_conditional` entries explicitly require `requires_modifier: "stem_separation_applied"` (manifest schema §5) as a narrow, named escape valve for pairs whose default (non-attenuated) rejection must not be read as blocking a specific more-advanced technique (e.g. `PAIR-SYN-E-007`, pair catalog).

## 6. Required baselines and comparability

### 6.1 Comparability classes

| Class | Meaning |
|---|---|
| `IDENTICAL_AUDIO_COMPARISON` | Same audio bytes/master run through both systems |
| `SAME_MASTER_LIKELY` | High confidence of the same master but bytes not independently verified identical |
| `CATALOG_EQUIVALENT` | Same catalog track but different provider/encode/master is plausible or confirmed |
| `NON_IDENTICAL_SOURCE_LIMITATION` | Comparison is on a materially different source |
| `SUBJECTIVE_REFERENCE_ONLY` | System cannot be run on our fixtures at all; observational quality reference only |

**Binding rule for statistical gates:** a comparability class weaker than `IDENTICAL_AUDIO_COMPARISON` may never supply the quantitative n-count for any P1-gate statistical test in §12.

### 6.2 Baseline systems

| # | System | Tier-1 | Tier-2 | Comparability | Notes |
|---|---|---|---|---|---|
| 1 | Fixed-duration equal-power crossfade | Our own reference implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` | Required, always-available quantitative baseline for `G1` |
| 2 | Clean cut / gapless | Our own reference implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` | Deterministic reference |
| 3 | Pinned SimpMusic AutoMix (actual) | If local-file playback is confirmed possible | Yes, via YouTube-resolved / Tidal-matched playback | Tier-1: `IDENTICAL_AUDIO_COMPARISON` if confirmed, else not runnable. Tier-2: `CATALOG_EQUIVALENT` | Score Auto-duration mode with DJ mode on and off separately |
| 3a | `SIMPMUSIC_CLASS_REFERENCE` (clean-room) | Our own Tier-1-runnable implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | Clean-room re-implementation of the published/pinned P0-M1 §6 formulas only, never GPLv3 source (P0-M1 §12 `REIMPLEMENT_CLEAN_ROOM` disposition). Guaranteed-available Tier-1 stand-in for `G2` when actual SimpMusic cannot consume Tier-1 fixtures |
| 4 | Echo Music AutoMix beta | `UNKNOWN_NEEDS_RUNTIME_PROOF` | Not established | Default `NON_IDENTICAL_SOURCE_LIMITATION` | Not load-bearing for any G-gate |
| 5 | Apple Music AutoMix | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Not load-bearing |
| 6 | Spotify playlist mixing `Auto` | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Not load-bearing |
| 7 | Algoriddim djay Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` | Yes | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON` pending verification; Tier-2 `CATALOG_EQUIVALENT` | Not load-bearing |
| 8 | Offtrack | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Not load-bearing |
| 9 | rekordbox Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` | Yes | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON` pending verification; Tier-2 `CATALOG_EQUIVALENT` | Not load-bearing |
| 10 | Future AutoMix engine revisions | Full Tier-1 corpus, every version | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | Internal regression-testing baseline |

No proprietary internals are invented for #4–#9; only publicly observable behavior, already-cited first-party documentation, or an explicit `UNKNOWN_NEEDS_RUNTIME_PROOF` flag.

### 6.3 SimpMusic baseline path

`G2` (§12) is satisfied either by actual SimpMusic (if local Tier-1 fixture playback is confirmed, `IDENTICAL_AUDIO_COMPARISON`) or by `SIMPMUSIC_CLASS_REFERENCE` (guaranteed Tier-1-runnable, `IDENTICAL_AUDIO_COMPARISON` by construction) if it is not — never by a `CATALOG_EQUIVALENT` Tier-2 session, which may only supply qualitative corroboration. A benchmark report must state which path was used.

## 7. Condition Registry

Named, reusable objective conditions referenced by `transition_class_policy.accepted_conditional` entries (manifest schema §5).

| Condition ID | Definition |
|---|---|
| `COND_BEAT_OK` | Beat-alignment error (beat-fraction) ≤ 1/16 (6.25%) at the chosen anchor point |
| `COND_DOWNBEAT_OK` | Downbeat/bar-phase error = 0 beat positions (requires a shared, defined meter between the two fixtures — not currently defined for cross-meter pairs, see `human_confirmation` in manifest schema §5 for that case) |
| `COND_CUE_OK` | Cue-region error = 0 ms (chosen entry/exit point lands inside an annotated acceptable region) |
| `COND_PHRASE_OK` | Phrase-boundary distance ≤ 0.5 × the local beat period |
| `COND_SECTION_OK` | Section-boundary distance ≤ 1 × the local bar period |
| `COND_TEMPO_ENVELOPE_OK` | Applied tempo-ratio deviation from 1.0 ≤ the pair's `manipulation_constraints.tempo_ratio_max_deviation` (default 12%) |
| `COND_PITCH_ENVELOPE_OK` | Pitch-shift magnitude ≤ the pair's `manipulation_constraints.max_pitch_shift_semitones` (default 3 semitones) |
| `COND_VOCAL_OK` | Vocal-overlap ratio ≤ 0.3 **and** vocal-overlap duration ≤ 2000 ms, **measured on the rendered/post-mix transition audio** (R12 — not naively on source-fixture `vocal_intervals_ms`; see §8) |
| `COND_BASS_OK` | Bass-overlap proxy covers ≤ the pair's `manipulation_constraints.low_band_coactivity_ratio_ceiling` (default 50%) of the transition window |
| `COND_LOUDNESS_OK` | Momentary loudness delta ≤ 2 LU |

Where no condition in this registry cleanly applies to a pair's specific structural situation (e.g. cross-meter downbeat compatibility), the pair's `accepted_conditional` entry may add a `human_confirmation` requirement (manifest schema §5) instead of being left with no path to acceptance at all, or being categorically `rejected` on the basis of a measurement gap rather than a genuine structural fact (R12).

**Default derivations** (unchanged from the first repair pass): `tempo_ratio_max_deviation` = 12% is set relative to SimpMusic's own shipped ±25% ceiling (P0-M1 §6), intentionally tighter, not merely matching it, pending empirical DSP-artifact-threshold testing once a prototype exists. The `C5`/`COND_BASS_OK` co-activity threshold (−12 dB relative to each track's own low-band peak, sustained ≥ 500 ms, ≤ 50% of the transition window) is derived in §10.

## 8. Objective metrics

Every metric is tagged `OBJECTIVE`, `PROXY`, or `HUMAN_ONLY`.

| Metric | Formula / method | Unit | Ground truth | Threshold/range | Class | Notes |
|---|---|---|---|---|---|---|
| Beat alignment error | `min(\|t_actual − t_nearest_grid_beat\|, beat_period − \|...\|)` | ms, beat-fraction | Beat timestamps | `COND_BEAT_OK`: ≤ 1/16 beat | `OBJECTIVE`/`PROXY` per source | |
| Downbeat/bar-phase error | Circular distance in beat positions | integer | Downbeat/bar-start annotations | `COND_DOWNBEAT_OK`: = 0 | `OBJECTIVE` | `N/A` for ambiguous/cross-meter fixtures — see `human_confirmation` escape (§7) |
| Cue-region error | Distance to nearest annotated acceptable region edge; 0 if inside | ms | Region annotations | `COND_CUE_OK`: = 0 | `OBJECTIVE`/`PROXY` per source | An **empty** region-annotation array is a valid, meaningful "no region exists" statement (manifest schema §3), distinct from a missing/`UNKNOWN` annotation |
| Phrase-boundary distance | `min(\|t − nearest_phrase_boundary\|)` | ms | Phrase annotations | `COND_PHRASE_OK`: ≤ 0.5 × beat period | `OBJECTIVE`/`PROXY` per source | |
| Section-boundary distance | Same method, section annotations | ms | Section annotations | `COND_SECTION_OK`: ≤ 1 × bar period | `PROXY` | |
| **Vocal overlap duration/ratio** | Sum of ms where **both tracks' rendered, post-mix vocal-band energy** is simultaneously above an audibility floor within the transition window; ratio = overlap / window duration | ms, ratio | Rendered transition audio, informed by (but not equal to) source `vocal_intervals_ms` | `COND_VOCAL_OK`: ratio ≤ 0.3, duration ≤ 2000 ms; `C4` (§10) | `PROXY` (real material); `OBJECTIVE` (synthetic, on the rendered signal) | **Redefined (R12):** measured on the actual rendered output, so a system that genuinely attenuates a track's vocal band during the overlap (`stem_separation_applied`) is scored on the resulting audible collision, not disqualified by source-level overlap that never reaches the listener |
| Bass-overlap proxy | Co-occurrence of both tracks' low-band (20–150 Hz) RMS ≥ threshold, sustained ≥ minimum duration | ms, ratio | Bass activity / raw low-band energy | `COND_BASS_OK`; `C5` (§10) | `PROXY` | Also computed on rendered output for the same reason as vocal overlap |
| Momentary loudness delta | `\|LUFS_momentary(t_post) − LUFS_momentary(t_pre)\|`, 400 ms window | LU | None beyond audio | `COND_LOUDNESS_OK`: ≤ 2 LU; `C6` | `OBJECTIVE` | |
| Short-term loudness continuity | 3 s-window loudness trend comparison | LU | None beyond audio | Scored per Lane C case | `OBJECTIVE` | |
| Transition-window loudness discontinuity | Max derivative of momentary (400 ms/100 ms hop) loudness curve vs. baseline | LU/s | None beyond audio | `C6` | `OBJECTIVE` | Momentary-basis, never labeled short-term |
| Energy-continuity delta/slope | Pre/post RMS-energy trend slope difference | dB/s | None beyond audio | Scored per Lane C case | `PROXY` | |
| Applied tempo ratio / max deviation | Executed vs. native playback rate | ratio, % | Engine-measured | `COND_TEMPO_ENVELOPE_OK`; `C7` | `OBJECTIVE` | |
| Pitch shift | `12·log2(f_shifted/f_original)` | semitones | Engine-measured | `COND_PITCH_ENVELOPE_OK`; `C8` | `OBJECTIVE` | |
| Click/pop/discontinuity/dropout candidate flag | Waveform-discontinuity/dropout detector | count, timestamps | None beyond audio | `C9` (two-stage) | `PROXY` | Raw flag is a candidate, never a confirmed defect on its own |
| Clipping / true-peak | ITU-R BS.1770-5 true-peak | dBTP | None beyond audio | ≤ −1 dBTP | `OBJECTIVE` | |
| Transition duration | Wall-clock executed transition window | ms | Engine-measured | Interpreted alongside class | `OBJECTIVE` | |
| Transition-class correctness | `observed_class` (§5.2) vs. `transition_class_policy`: `accepted_unconditional` → correct; `accepted_conditional` → correct iff conditions (+ `human_confirmation`/`requires_modifier` where present) are satisfied; else mismatch, and a `rejected`-class mismatch grounds `C11` | categorical + confusion matrix | `transition_class_policy` | `G4` (§12) | `PROXY` | Evaluated exclusively against `observed_class`, never `engine_reported_class` (§5.2) |

## 9. Human listening rubric

Human listening is **mandatory** and has **veto authority** over any automated PASS.

### 9.1 Scale

Anchored 1–5 (dimensions 1–15): 1 = clearly broken, 2 = poor, 3 = acceptable, 4 = good, 5 = excellent. `N/A` always valid.

### 9.2 Scored dimensions

1–15: entry-point naturalness, exit-point naturalness, beat coherence, downbeat/bar coherence, phrase coherence, section coherence, vocal handling, bass/frequency handling, energy flow, loudness continuity, tempo/stretch naturalness, pitch/key naturalness, DSP smoothness, transition-style appropriateness, overall musical intentionality.

**Dimension 16 — Preference vs. baseline**: every pair is played blinded, order-randomized, in both its candidate-system and fixed-equal-power-crossfade-baseline rendering. The listener records exactly one of `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE`. Plus an independent veto flag: `CATASTROPHIC_FAILURE_OBSERVED: yes/no + code (§10) + note`, which forces pair `FAIL` regardless of every other score.

**`human_confirmation` rubric checks (new — R12):** when a pair's `transition_class_policy` includes a `human_confirmation` requirement (manifest schema §5, e.g. `PAIR-SYN-A-010`), the listener additionally rates the named dimension against the stated `min_score` as part of the same blinded session — this is not a separate procedure, just an additional required field on that pair's rubric record.

### 9.3 Procedure

Blinded/randomized, single-owner initially with a defined multi-rater upgrade path (inter-rater agreement reported per dimension once ≥2 raters exist; disagreement ≥2 points is reported as a distribution, never averaged away). Every human-rated pair records rater ID, timestamp, playback order, and blinding self-check.

## 10. Catastrophic failures

Any **confirmed** code triggers pair `FAIL`, independent of aggregate averages, and counts toward `G6`. A human veto independently triggers `FAIL`, gated as `G7`.

| Code | Definition | Threshold / detection |
|---|---|---|
| `C1_BEAT_TRAINWRECK` | Sustained audible beat drift on a beat-synced pair | Beat-alignment error > 1/8 beat for > 50% of the overlap window, BPM gap ≤ 3% | Safety-critical |
| `C2_BAR_PHASE_ERROR` | Wrong beat-in-bar on a bar-synced pair | Downbeat/bar-phase error > 0 beat positions | Safety-critical |
| `C3_WRONG_PHRASE_LOCATION` | Entry/exit far outside any acceptable region | Cue-region error exceeds a phrase/8-bar distance, for `observed_class ∈ {FULL_DJ_BLEND, SHORT_EQ_BLEND}` | |
| `C4_SEVERE_VOCAL_COLLISION` | Two independently active vocal lines overlap heavily, **measured on rendered audio** | Vocal-overlap ratio > 60% and duration > 4 s | Safety-critical |
| `C5_SEVERE_BASS_MASKING` | Full-energy bass-on-bass collision in a short transition | Bass co-activity (≥ `low_band_coactivity_threshold_db`, sustained ≥ `low_band_coactivity_min_duration_ms`) covers > 50% of a window < 4000 ms | |
| `C6_GROSS_LOUDNESS_DISCONTINUITY` | Audible loudness jump, momentary basis only | > 6 LU momentary jump between consecutive 100 ms-stepped measurements, or > 3 LU momentary step at a `CUT`/`GAPLESS` splice | Safety-critical |
| `C7_STRETCH_ARTIFACT` | Tempo correction produces an audible artifact | Applied deviation exceeds `tempo_ratio_max_deviation` **and** human DSP-smoothness (dim. 13) ≤ 2 | |
| `C8_PITCH_ARTIFACT` | Pitch correction produces an audible artifact | Shift exceeds `max_pitch_shift_semitones`, or any shift paired with human pitch/key-naturalness (dim. 12) ≤ 2 | |
| `C9_CLICK_POP_DROPOUT` | Audible discontinuity/dropout at the splice/commit boundary | Two-stage: `C9_CANDIDATE` (detector fires; logged only, no gate consequence) → `C9_CONFIRMED` (corroborated by a deterministic dropout/underrun, or a blinded human rating dim. 13 ≤ 2 / veto within ±250 ms) | Safety-critical, confirmed form only |
| `C10_WRONG_METADATA_POISONING` | Engine's BPM/key input diverges from fixture ground truth and measurably drives a bad decision | Input BPM off > 3 (non-half/double-time) or key off > 1 Camelot step, traceable to the resulting decision | |
| `C11_FORCED_WRONG_TRANSITION_STYLE` | Engine's `observed_class` (§5.2) appears in the pair's explicit, fixture-grounded `rejected` list, corroborated by evidence | Fires only when (a) `observed_class ∈ transition_class_policy.rejected` **and** (b) an objective metric breach or a human rating ≤2 / veto on transition-style appropriateness (dim. 14) | |

"Safety-critical" codes (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`, `HUMAN_VETO`) require **zero** occurrences on the Tier-1 holdout split (`G6`/`G7`, §12).

**`C5` co-activity threshold derivation:** −12 dB relative to each track's own low-band peak (≈25% of peak amplitude, a standard "clearly active" cutoff), sustained ≥ 500 ms (excludes brief incidental overlaps).

## 11. Anti-overfitting

The benchmark must not be EDM/4-on-the-floor-only. Coverage plan: pop, hip-hop, R&B, rock, electronic, acoustic, ballad, dynamic-tempo/live material where legally obtainable, unusual intros/outros, non-4/4 cases. Holdout pairs/categories may not be hand-tuned — any threshold/heuristic/fixture adjustment made in response to a specific holdout pair's result invalidates that holdout pair.

## 12. P0 → P1 gate

P1 (local AutoMix engine **production** implementation) remains **BLOCKED** until `G1`–`G8` all pass. This blocks the production, shipping engine only — a disposable P0-M3 benchmark-execution prototype that exists solely to produce this gate's own evidence is not itself blocked by it.

### Minimum corpus / gate sample-size plan (R10 — revised)

Machine-readable source of truth: `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §2 `manifest.json.corpus_minimums`.

- **Tier-1 total corpus minimum: 74 pairs**, split `dev` 52 / `holdout` **22** (increased from the first repair pass's 18 — see the `G1` tie-safety fix below).
- **Per-lane minimum**: Lane A ≥ 23, Lane B ≥ 8, Lane C ≥ 8, Lane D ≥ 12, Lane E ≥ 23 (sums to 74). A and E were both increased from 16 to 23 (+7 each) to absorb the corpus-wide increase from 60→74 while preserving their original weighting rationale (P0-M1 §16's beat/downbeat/cue/phrase floor, and SimpMusic's documented no-per-pair-fallback gap respectively).
- **Lane A "clean structure" subset** (used by `G3`): minimum **10 total, holdout ≥ 3** (new explicit field — R10; `dev` implied 7).
- **Lane E "should-not-full-blend" adversarial subset** (used by `G4`'s `C11` zero-tolerance check): minimum **8 total, holdout ≥ 3** (new explicit field — R10; `dev` implied 5).
- **`G2` SimpMusic-comparison subset**: fixed 30-pair subset, `dev` 21 / `holdout` 9 (unchanged from the first repair pass).

### G1 — Materially better blind human preference than fixed-duration equal-power crossfade

Recorded as `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE` per §9.2, **one outcome per distinct pair** — repeated ratings of the same pair (e.g. by multiple raters in the multi-rater phase, or repeat sessions) are aggregated to a single decisive/tie outcome for that pair before entering the binomial computation (by majority vote among raters for that pair; an exact rater tie on a given pair is itself recorded as `TIE` for that pair). **A pair never contributes more than one binomial trial to `G1`, regardless of how many times it was rated** — this is the direct fix for the PM's "do not count repeated ratings of the same pair as independent binomial trials" instruction.

**Tie handling:** ties excluded from the win-rate ratio (`win_rate = CANDIDATE_PREFERRED / (CANDIDATE_PREFERRED + BASELINE_PREFERRED)`, decisive trials only), always reported alongside `tie_rate = TIE / n_total`. If `tie_rate > 20%`, the check is inconclusive regardless of win rate among decisive trials, and more **distinct** pairs (never repeat-ratings of existing pairs) must be added under the same protocol.

**R10 fix — the holdout pool must be tie-rate-robust, not just large enough in the zero-tie case:** the first repair pass set the Tier-1 holdout minimum to exactly 18 (matching `G1`'s stated `n ≥ 18 decisive` holdout requirement), which meant a single tied pair already made the corpus incapable of satisfying `G1` even though a 1-in-18 (5.6%) tie rate is far inside the 20% inconclusive ceiling. The holdout minimum is now **22**: `22 − floor(0.20 × 22) = 22 − 4 = 18` — 22 is the smallest pool size for which the *maximum* tie count still compliant with the 20% ceiling (4 ties, an 18.2% tie rate) still leaves exactly 18 decisive trials. This is a worst-case guarantee: any holdout tie rate up to and including 20% at n=22 is arithmetically proven not to starve `G1` below its required 18 decisive trials.

**Threshold:** one-sided exact binomial test against null `p₀ = 0.5` (`H₁: p > 0.5`):

- Combined `dev`+`holdout`: `n ≥ 40` decisive trials, win rate ≥ 65%, exact binomial `p < 0.05`.
- `holdout` alone: `n ≥ 18` decisive trials (guaranteed by the 22-pair pool above under the tie-rate ceiling), win rate ≥ 60%. Documented as a point-estimate corroboration, not independently significance-tested at this sample size (unchanged rationale from the first repair pass).

**Non-zero-tie worked example (R10 REQUIRED VALIDATION item 2):** with the 22-pair holdout pool at its worst-case-compliant tie count:

| Scenario | Holdout pool (n) | Ties | Tie rate | Decisive trials | Decisive wins needed for 60% | Result |
|---|---|---|---|---|---|---|
| Worst-case-compliant tie rate | 22 | 4 | 18.2% (≤ 20% ceiling — still conclusive) | **18** | 11 (61.1%) | 18 decisive trials achieved exactly at the boundary — `G1`'s `n ≥ 18 decisive` requirement is met even at the maximum tie count the corpus is required to tolerate |
| Realistic illustrative case | 22 | 2 | 9.1% | 20 | 12 (60.0%) | More decisive trials than the worst case, comfortably above the n≥18 floor |
| Prior (repaired-but-still-broken) design | 18 | 1 | 5.6% (well inside the 20% ceiling) | **17** | — | **Fails `G1`'s own n≥18 decisive requirement** despite a tie rate far inside the stated inconclusive threshold — this is the exact defect R10 fixes; a holdout pool sized only to the decisive-trial floor with zero tolerance for ties is not tie-rate-robust |

The third row is included specifically to demonstrate the defect the PM identified and prove the 22-pair fix resolves it, per REQUIRED VALIDATION item 2's instruction to "prove the declared minimum corpus can still reach 18 distinct decisive holdout pairs."

Exact binomial boundary table (unchanged from the first repair pass, still valid — computed via exact summation, not normal approximation):

| n | k (wins) | Win rate | Exact one-sided p-value | Passes p<0.05? |
|---|---|---|---|---|
| 40 | 26 | 65.0% | 0.0403 | Yes |
| 40 | 25 | 62.5% | 0.0769 | No |
| 18 | 11 | 61.1% | 0.2403 | No (confirms holdout-alone is a point estimate, not independently significant) |
| 18 | 10 | 55.6% | 0.4073 | No |

### G2 — Materially better quality/preference than SimpMusic-class AutoMix

Via §6.3's baseline path, mean overall-preference (dim. 15) ≥ SimpMusic-class score + 0.5, on the 30-pair `G2` subset, `n ≥ 30` combined, `holdout n ≥ 9` (unchanged).

### G3 — Real beat/downbeat/cue/phrase-aware behavior

On the Lane-A "clean structure" subset: median beat-alignment error ≤ 1/16 beat and median downbeat/bar-phase error = 0 for beat/bar-synced pairs; entry/exit inside an acceptable region in ≥ 90% of those pairs, `n ≥ 10` combined. **R10 fix:** this threshold must now also hold independently on the subset's `holdout` portion, `n ≥ 3` — at this size, "≥90%" resolves to an integer requirement of **all 3** holdout pairs succeeding (`ceil(0.9×3) = 3`), stated explicitly as a coarse pass/fail check at small n rather than a loosely fractional target, consistent with how `G1`'s holdout check is disclosed as a point estimate rather than a finely-grained statistic.

### G4 — Confidence-aware fallback

On all Lane E pairs (`n ≥ 23`): transition-class match rate (§8, evaluated against `observed_class`, §5.2) ≥ 80% overall. On the Lane E "should-not-full-blend" adversarial subset (`n ≥ 8`): `C11` confirmed-event rate = 0%. **R10 fix:** both checks must also hold independently on `holdout` — Lane E overall holdout portion (drawn from Lane E's 23-pair total at the standard ~30% ratio, ≥ 7) and the adversarial subset's `holdout n ≥ 3` (new explicit field). At `n=3`, the `C11` zero-tolerance check remains a clean integer requirement (0 of 3) regardless of sample size, so this holdout check does not carry the same small-n fractional-threshold caveat as `G3`'s.

### G5 — Success on unseen holdout pairs

Every threshold in `G1`–`G4` must hold independently on each gate's own **explicitly-defined** holdout component: 18 decisive (`G1`, guaranteed by the 22-pair tie-robust pool), 9 (`G2`), 3 (`G3`'s clean-structure subset), 3 (`G4`'s adversarial subset) — every one of these is now a named field in `manifest.json.corpus_minimums` (schema §2), closing the R10 defect where `G5` referred to "each subset's own holdout portion" without any of those portions being machine-readably defined. No pair-specific tuning is permitted on holdout (§11).

### G6 — Catastrophic failure rate ceiling

With the 74-pair Tier-1 corpus: ≤ 2% of all scored pairs may trigger any confirmed `C1`–`C11` code — `floor(0.02 × 74) = 1` pair. **Zero** confirmed safety-critical events (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`) on the 22-pair holdout subset.

### G7 — No human-veto catastrophic failures hidden by aggregate averages

`HUMAN_VETO` rate ≤ 1 of 74 pairs overall, **0** on the 22-pair holdout subset.

### G8 — Reproducible Tier-1 results

Re-running the full Tier-1 pipeline against the same pinned engine commit and manifest must reproduce identical objective-metric values (or a documented tolerance for any non-deterministic step); a reproduction checklist must exist and be exercised once before a `PASS` claim.

Apple Music AutoMix / djay / Offtrack / Spotify / rekordbox are **stretch references** — any benchmark report must state the observed gap against each honestly, not omit or soften it.

## 13. Stop / re-scope conditions

`RE-SCOPE` or `STOP` should be triggered if evidence, once this contract is executed against a real prototype, shows: cue/downbeat/phrase work does not materially improve over SimpMusic-class behavior (`G2`) despite implementation effort; quality remains substantially behind Offtrack/djay with no compensating advantage; real-time analysis is too expensive for target hardware; quality collapses outside a narrow genre set (§11); the confidence-aware fallback mechanism (`G4`) cannot reliably suppress catastrophic mixes even after dev-split tuning; a required capability depends on legally unavailable provider integration; or existing permissive open components already solve nearly everything this benchmark measures with no defensible improvement opportunity for a custom planner.

## 14. Scope discipline

This document and its companions are **specification/research artifacts only**. No AutoMix engine implementation and no audio fixtures are included. Disposable/benchmark-execution prototyping is explicitly in scope for a future P0-M3 task; the shipping production engine is not. Every third-party capability claim in §6 is either already-cited first-party documentation or explicitly `UNKNOWN_NEEDS_RUNTIME_PROOF` — no proprietary internals are invented. **P0-M3 is explicitly not started by this deliverable.**

## 15. Acceptance criteria check

See the `HANDOFF TO PM — FINAL REPAIR` section of the PM-facing report for the line-by-line AC check and the R10–R12 repair-item-by-repair-item evidence trail.
