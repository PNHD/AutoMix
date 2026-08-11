# P0-M2-R1 — AutoMix Quality Benchmark Contract

Status date: 2026-08-11 (PM REVIEW #3 — final schema/taxonomy repair)

## 0. Execution profile actually used

- **Execution agent:** Claude Code (Claude Agent SDK CLI), continuing the same session (commits `0d7ba89`, `d3c9f8b`, `3f0299a`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High (owner/PM Desktop-UI attestation, not independently introspectable — explicitly not a stop condition per Issue #4 and all three PM reviews).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **This revision addresses** `PM REVIEW #3 — FINAL SCHEMA/TAXONOMY REPAIR REQUIRED` (Issue #4, posted 2026-08-11T06:06:59Z), items R13–R16. R10–R12 (holdout sample sizes, taxonomy existence, first rejected-pair re-audit) were confirmed correct by this review and are carried forward unchanged in substance below; R13–R16's fixes are marked inline.

## 1. Result

**PASS**

All Issue #4 acceptance criteria remain satisfied (§15). This revision closes the four remaining schema/taxonomy defects the PM's third review identified: `FULL_DJ_BLEND` no longer requires unnecessary tempo/pitch automation (R13); `GAPLESS` can no longer be assigned to a transition with a positive, unmeasured, audible gap (R14); `PAIR-SYN-A-010`'s two-dimension human-confirmation requirement and `PAIR-SYN-E-007`'s conditional-accept/conditional-reject policy are now both fully schema-representable with no prose-only boolean logic (R15); and `G4`'s Lane-E overall holdout check now has an explicit, machine-readable minimum and integer threshold, with `G5` listing both of `G4`'s holdout requirements (R16).

## 2. Purpose

Define the benchmark contract deciding whether AutoMix is musically better than naive crossfade/BPM-key-only mixing, and whether P1 is allowed to start. This document, `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`, and `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md` are the full deliverable set. No AutoMix engine code, no audio files. P0-M3 may build disposable, non-production benchmark-execution prototypes to actually run this contract; only the shipping production engine is blocked pending the gate.

## 3. Core benchmark principle

**BPM/key compatibility is never sufficient evidence of AutoMix quality**, per `docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §8–§10: the pinned SimpMusic baseline is `TEMPO_AWARE` with working Camelot key-compatibility scoring, yet has zero beat-timestamp, downbeat, phrase, section, or content-activity awareness, and its incoming-track start position is unconditionally `0` regardless of the outgoing track's phase. This benchmark must detect failures in cue-point choice, beat phase, downbeat/bar alignment, phrase alignment, section-aware entry/exit, vocal collision, bass/percussion masking, energy trajectory, loudness continuity, tempo-stretch artifacts, pitch-shift artifacts, clicks/pops/discontinuities, transition-style appropriateness, and confidence/fallback behavior.

Symmetrically, the benchmark must not punish an engine for succeeding at a pair that only looks adversarial on paper, must not confuse "this benchmark cannot currently measure success here" with "success is impossible," and — the specific subject of this revision — **must not classify a transition's style by which DSP technique happened to be used rather than by its observable musical outcome** (R13/R15), and must not treat the mere absence of measured overlap as proof of a seamless join (R14).

### 3.1 Terminology gate (binding, per `.agents/skills/automix-forensic-research/SKILL.md`)

| Term | Meaning | Not satisfied by |
|---|---|---|
| Tempo/BPM-aware | scalar or estimated tempo used | — |
| Beat-aware | explicit beat timestamps/grid used | a derived `60000/BPM` theoretical grid (SimpMusic's actual mechanism, P0-M1 §8 level 2) |
| Downbeat-aware | bar starts/downbeats identified and used | beat-awareness alone |
| Phrase-aware | transition entry/exit uses phrase boundaries | downbeat-awareness alone, or a fixed "every 32 beats" proxy (P0-M0 §7.2) |
| Section-aware | intro/verse/chorus/outro or equivalent structural sections identified and used | phrase-awareness alone |

Every benchmark report must classify the system under test against this table explicitly, using the same eight-level scheme P0-M1 §8 used for SimpMusic.

## 4. Benchmark lanes

Each lane is scored independently; a single aggregate score is disallowed. Every case type must have at least one corresponding fixture/pair in the manifest; concrete representative pairs are in `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`.

### 4.1 Lane A — Timing / structure

Same BPM but wrong beat phase · beat-aligned but wrong downbeat/bar phase · same BPM/key but incompatible phrase timing · intro/outro opportunities · chorus/drop/build-up boundaries · pickup/anacrusis starts · long silence/non-musical tails · tracks without clean intro/outro · variable tempo where feasible · non-4/4 or ambiguous meter where feasible.

"Adversarial" describes the *input*, not the required *output*. A system that measurably corrects a mismatch before executing a full blend is scored as having succeeded, not as having chosen the wrong class (§6/§7). Where no objective condition is defined for a specific kind of correction (e.g. cross-meter downbeat compatibility, `PAIR-SYN-A-010`), the pair routes to mandatory human confirmation rather than categorical rejection.

### 4.2 Lane B — Content collision

vocal→vocal · sustained vocal outro→vocal intro · dense bass→dense bass · percussion-heavy overlap · instrumental→vocal · sparse→dense · dense→sparse.

The vocal/bass-overlap objective metrics (§8) are computed against the **rendered, post-mix** transition audio, not naively against source-fixture activity annotations — a system applying genuine stem/vocal attenuation, ducking, or any other mitigation technique during the overlap is scored on the resulting audible collision, never disqualified merely because the untouched source fixtures overlap, and never required to use one specific named technique (§5.5).

### 4.3 Lane C — Energy / loudness

high→high · low→high · high→low · gradual buildup/drop · large mastering-loudness differences · locally quiet transition region despite high integrated loudness. Loudness terminology is binding: `momentary` = 400 ms, `short-term` = 3 s, `integrated` = programme/start-stop-style gated measurement, all via ITU-R BS.1770-5 with EBU R128/Tech 3341 window-naming.

### 4.4 Lane D — Harmonic / tempo

compatible key + close tempo · compatible key + large tempo gap · incompatible key + close tempo · half/double-time cases · pitch shifting helps · pitch shifting should be avoided · stretch within reasonable range · stretch outside reasonable range. Per-pair `manipulation_constraints` define "safe correction range" concretely (§7).

### 4.5 Lane E — Confidence / fallback

Corpus must contain pairs where the expected preferred behavior is `FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, `SIMPLE_CROSSFADE`, `GAPLESS`, `CUT`, or `NO_SPECIAL_TRANSITION` (§5 defines each operationally). This lane scores whether the **chosen transition class** was appropriate, not only whether DSP execution was smooth. Lane E carries a dedicated internal subset — pairs whose `transition_class_policy` categorically excludes `FULL_DJ_BLEND` for a real, fixture-grounded or outcome-grounded reason — used by the `C11`/`G4` zero-tolerance check (§10/§12).

## 5. Transition-Class Taxonomy (revised — R13/R14/R15)

**Binding, operational definitions**, owned by the benchmark runner via observable, measured evidence — never by a candidate engine's self-reported label.

### 5.1 Class definitions

| Class | Overlap | Beat/downbeat sync | Duration | Automation | Cue-point selection |
|---|---|---|---|---|---|
| `GAPLESS` | Zero overlap **and** zero (sample-contiguous, within epsilon) gap | N/A | 0 ms by definition | None | N/A — natural boundaries both sides |
| `NO_SPECIAL_TRANSITION` | Zero overlap; gap may be zero **or** a measurable positive silence | N/A | Same as `GAPLESS` at the processing level | None | N/A — natural boundaries both sides |
| `CUT` | Zero overlap; gap may be zero or positive | N/A | Same | None | Yes — at least one boundary is *not* the fixture's own natural/authored boundary |
| `SIMPLE_CROSSFADE` | Nonzero | Not required for the label | Not hardcoded | Volume/gain only | Yes |
| `SHORT_EQ_BLEND` | Nonzero | Not required for the label | Not hardcoded | Volume/gain + EQ/filter; no tempo/pitch | Yes |
| `FULL_DJ_BLEND` | Nonzero | **Contractual expectation of the label** (§5.2 rule 3), established by **either** tempo/pitch automation **or** demonstrated sustained beat/downbeat lock — not both required | Not hardcoded | Volume/gain, optionally EQ, optionally tempo/pitch | Yes, expected |

**R13 fix, stated plainly:** the prior taxonomy required `has_tempo_pitch_automation = true` for `FULL_DJ_BLEND` unconditionally, penalizing the better engineering choice of leaving two already-tempo/phase-compatible tracks untouched. `FULL_DJ_BLEND` is now earned by **either** (a) tempo/pitch automation being present — the label does not require it to *succeed*, quality is scored separately via `COND_TEMPO_ENVELOPE_OK`/`C7` — **or** (b) EQ automation **plus** measured, sustained beat/downbeat lock evidence (§5.3): a demonstrated, non-coincidental, structurally deliberate synchronization achieved *without* needing correction because the tracks were already compatible. A bare volume-only fade that merely touches a beat does **not** qualify under either path (§5.2 rule 3d/3e).

Duration is deliberately never used as a hard classification threshold anywhere in this table.

### 5.2 Classification decision procedure (deterministic, runner-applied)

Given a transition render record (manifest schema §10):

1. Measure `overlap_ms` and, if `overlap_ms` is at or below the epsilon (default 20 ms), measure `inter_track_gap_ms` (**mandatory** in that branch — a missing value is never defaulted to zero; **R14**).
2. **If `overlap_ms ≤ epsilon`:**
   a. If `inter_track_gap_ms` is missing/`null` → `observed_class = UNCLASSIFIED_ANOMALY` (a zero-overlap render with no measured gap is an instrumentation failure, not a valid classification input).
   b. If `inter_track_gap_ms ≤ epsilon` (sample-contiguous join): measure `outgoing_used_natural_full_duration` and `incoming_used_natural_start`.
      - Both `true` **and** `is_continuous_work = true` → `GAPLESS`.
      - Both `true` **and** `is_continuous_work = false` → `NO_SPECIAL_TRANSITION`.
      - Not both `true` (a truncation or non-natural start occurred) → `CUT`.
   c. If `inter_track_gap_ms > epsilon` (a real, measurable, audible gap): **`GAPLESS` is never assigned in this branch, regardless of `is_continuous_work` or boundary naturalness** (R14's binding rule).
      - Both boundaries natural → `NO_SPECIAL_TRANSITION` (natural sequential playback with an incidental gap — no special transition logic was applied to close it, so it is not `GAPLESS`).
      - Not both natural → `CUT`.
3. **If `overlap_ms > epsilon`:**
   a. If `has_volume_automation = false` → `observed_class = UNCLASSIFIED_ANOMALY`.
   b. Else if `has_eq_automation = false` **and** `has_tempo_pitch_automation = false` → `SIMPLE_CROSSFADE` (regardless of `has_sustained_beat_lock` — a bare volume-only fade is never promoted to `FULL_DJ_BLEND` merely by coincidentally tracking the beat grid).
   c. Else if `has_tempo_pitch_automation = true` → `FULL_DJ_BLEND` (independently sufficient, regardless of `has_eq_automation` or lock quality — execution quality is scored separately by `COND_TEMPO_ENVELOPE_OK`/`COND_PITCH_ENVELOPE_OK`/`C7`/`C8`, never by the classification step).
   d. Else if `has_eq_automation = true` **and** `has_sustained_beat_lock = true` → `FULL_DJ_BLEND` (**R13 fix**: the no-tempo/pitch-needed path).
   e. Else (`has_eq_automation = true`, `has_tempo_pitch_automation = false`, and `has_sustained_beat_lock` is `false` or `null`) → `SHORT_EQ_BLEND` — the "good effort, not confirmed beat-locked" tier.
4. `class_label_mismatch = (engine_reported_class != observed_class)`, diagnostic only.

`engine_reported_class` is never consulted in steps 1–3. This is the complete answer to "the benchmark, not the candidate engine, must own class assignment for gate purposes": `observed_class` is a pure function of measured render-time signals plus static, pre-authored fixture/pair annotations.

### 5.3 Sustained beat/downbeat lock — classification evidence (new — R13)

`sustained_beat_lock_ratio` (manifest schema §10): using each track's own beat timestamps mapped through its **actually-applied** playback-rate curve (native/constant when `has_tempo_pitch_automation = false`, else the measured curve), compute — for beat-grid instants within the overlap window — the fraction where **both** instantaneous beat-alignment error ≤ 1/16 beat (`COND_BEAT_OK`'s own threshold, reused for consistency) **and** downbeat-phase error = 0, simultaneously, relative to a shared beat/bar grid.

`has_sustained_beat_lock = true` iff:
- `sustained_beat_lock_ratio ≥ 0.8` (at least 80% of beat-grid instants in the window are simultaneously beat- and bar-locked), **and**
- `overlap_ms ≥ 4 × local_bar_period_ms` (a minimum-duration floor distinguishing *sustained* lock from a single lucky beat-aligned instant).

Both are `null` when reliable beat ground truth (`SYNTHETIC_EXACT`/`MANUAL`) is unavailable for either track — never imputed `false` (which would silently deny the no-automation-needed path) or `true` (which would silently grant it). A pair lacking such ground truth simply cannot use rule 3d; a candidate engine's blend on it can still classify `FULL_DJ_BLEND` via rule 3c (tempo/pitch automation) if applicable, or is capped at `SHORT_EQ_BLEND` otherwise — correct, conservative behavior given missing evidence, not a benchmark defect.

**Data classification:** `sustained_beat_lock_ratio` is `OBJECTIVE` when computed against `SYNTHETIC_EXACT`/`MANUAL` beat ground truth, `PROXY` when computed against `MODEL_ESTIMATE` ground truth (consistent with every other metric's source-dependent tagging in §8).

### 5.4 Worked classification examples (R13/R14 REQUIRED VALIDATION)

| # | Scenario | Key measured signals | `observed_class` | Rule applied |
|---|---|---|---|---|
| **A** | Same-tempo, already beat/phase-aligned, phrase-aware DJ blend; **no** tempo/pitch automation | `overlap_ms=18000`, `has_volume_automation=true`, `has_eq_automation=true`, `has_tempo_pitch_automation=false`, `sustained_beat_lock_ratio=0.94` over an 18 s window at 120 BPM (bar period 2000 ms; `4×`=8000 ms ≤ 18000 ms) → `has_sustained_beat_lock=true` | **`FULL_DJ_BLEND`** | Rule 3d |
| **B** | Beat-matched full DJ blend requiring time-stretch (tracks natively 8% apart) | `overlap_ms=25000`, `has_volume_automation=true`, `has_eq_automation=true`, `has_tempo_pitch_automation=true` (applied ratio within `tempo_ratio_max_deviation`) | **`FULL_DJ_BLEND`** | Rule 3c (tempo/pitch automation alone is sufficient) |
| **C** | EQ crossfade without sustained structural/beat synchronization | `overlap_ms=12000`, `has_volume_automation=true`, `has_eq_automation=true`, `has_tempo_pitch_automation=false`, `sustained_beat_lock_ratio=0.35` (below the 0.8 floor) → `has_sustained_beat_lock=false` | **`SHORT_EQ_BLEND`** (not `FULL_DJ_BLEND`) | Rule 3e |
| **D** | Natural boundary, `gap_ms = 0` (sample-contiguous), fixtures authored `is_continuous_work=true` | `overlap_ms=0`, `inter_track_gap_ms=0`, both natural | **`GAPLESS`** | Rule 2b, continuous-work branch |
| **D'** | Same as D but `is_continuous_work=false` | Same measured signals, different annotation | **`NO_SPECIAL_TRANSITION`** (not `GAPLESS`) | Rule 2b, non-continuous branch — shows `GAPLESS` depends on the authored-continuity fact, not the waveform alone |
| **E** | Natural boundary, positive audible gap (e.g. 1500 ms measured silence) | `overlap_ms=0`, `inter_track_gap_ms=1500` (> 20 ms epsilon), both natural | **`NO_SPECIAL_TRANSITION`** (never `GAPLESS`) | Rule 2c — proves R14's binding rule |

Rows A and B both classify `FULL_DJ_BLEND`, proving R13 (neither tempo/pitch automation nor its absence alone determines the label). Row C classifies `SHORT_EQ_BLEND`, proving the taxonomy still distinguishes a genuine sustained DJ blend from an unsynchronized EQ crossfade. Rows D/D'/E together prove `GAPLESS` requires zero overlap *and* zero gap *and* authored continuity — any one failing forecloses it.

### 5.5 Stem/source-separation and other techniques — diagnostic only, never gating (R15)

`stem_separation_applied` (manifest schema §10) records whether the system under test applied stem/source-separation or targeted attenuation, purely as **diagnostic metadata**. It is never referenced by any `transition_class_policy` entry or classification rule after this revision. Where a pair's acceptance of a class depends on an audible outcome achievable by more than one technique (e.g. avoiding a vocal collision via stem separation, dynamic ducking, spectral separation, or alternate cue-point handling), the policy is written in terms of the **outcome condition** (e.g. `COND_VOCAL_OK`, measured on rendered audio regardless of mechanism) via `rejected_conditional` or `accepted_conditional` (manifest schema §5) — never a named technology. See `PAIR-SYN-E-007` in the pair catalog for the worked example.

## 6. Required baselines and comparability

### 6.1 Comparability classes

| Class | Meaning |
|---|---|
| `IDENTICAL_AUDIO_COMPARISON` | Same audio bytes/master run through both systems |
| `SAME_MASTER_LIKELY` | High confidence of the same master but bytes not independently verified identical |
| `CATALOG_EQUIVALENT` | Same catalog track but different provider/encode/master is plausible or confirmed |
| `NON_IDENTICAL_SOURCE_LIMITATION` | Comparison is on a materially different source |
| `SUBJECTIVE_REFERENCE_ONLY` | System cannot be run on our fixtures at all; observational quality reference only |

**Binding rule:** a comparability class weaker than `IDENTICAL_AUDIO_COMPARISON` may never supply the quantitative n-count for any P1-gate statistical test in §12.

### 6.2 Baseline systems

| # | System | Tier-1 | Tier-2 | Comparability | Notes |
|---|---|---|---|---|---|
| 1 | Fixed-duration equal-power crossfade | Our own reference implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` | Required, always-available `G1` baseline |
| 2 | Clean cut / gapless | Our own reference implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` | Deterministic reference |
| 3 | Pinned SimpMusic AutoMix (actual) | If local-file playback confirmed | Yes, via YouTube-resolved/Tidal-matched playback | Tier-1 `IDENTICAL_AUDIO_COMPARISON` if confirmed, else not runnable. Tier-2 `CATALOG_EQUIVALENT` | Score Auto-duration with DJ mode on and off separately |
| 3a | `SIMPMUSIC_CLASS_REFERENCE` (clean-room) | Our own Tier-1-runnable implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | Clean-room re-implementation of P0-M1 §6's published formulas only, never GPLv3 source. Guaranteed-available `G2` stand-in |
| 4 | Echo Music AutoMix beta | `UNKNOWN_NEEDS_RUNTIME_PROOF` | Not established | `NON_IDENTICAL_SOURCE_LIMITATION` default | Not load-bearing |
| 5 | Apple Music AutoMix | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY`/`CATALOG_EQUIVALENT` | Not load-bearing |
| 6 | Spotify playlist mixing `Auto` | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY`/`CATALOG_EQUIVALENT` | Not load-bearing |
| 7 | Algoriddim djay Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` | Yes | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON`; Tier-2 `CATALOG_EQUIVALENT` | Not load-bearing |
| 8 | Offtrack | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY`/`CATALOG_EQUIVALENT` | Not load-bearing |
| 9 | rekordbox Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` | Yes | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON`; Tier-2 `CATALOG_EQUIVALENT` | Not load-bearing |
| 10 | Future AutoMix engine revisions | Full Tier-1 corpus, every version | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | Internal regression baseline |

No proprietary internals are invented for #4–#9; only publicly observable behavior, already-cited first-party documentation (P0-M0), or an explicit `UNKNOWN_NEEDS_RUNTIME_PROOF` flag.

### 6.3 SimpMusic baseline path

`G2` is satisfied either by actual SimpMusic (if local Tier-1 fixture playback is confirmed, `IDENTICAL_AUDIO_COMPARISON`) or by `SIMPMUSIC_CLASS_REFERENCE` (guaranteed Tier-1-runnable, `IDENTICAL_AUDIO_COMPARISON` by construction) if not — never by a `CATALOG_EQUIVALENT` Tier-2 session, which may only supply qualitative corroboration. A benchmark report must state which path was used.

## 7. Condition Registry

Named, reusable objective conditions referenced by `transition_class_policy` entries (manifest schema §5). These govern **acceptance quality** of an already-classified transition; they are distinct from — and never substitute for — the §5.3 classification-evidence signals, which govern **which class was rendered in the first place**.

| Condition ID | Definition |
|---|---|
| `COND_BEAT_OK` | Beat-alignment error (beat-fraction) ≤ 1/16 (6.25%) at the chosen anchor point |
| `COND_DOWNBEAT_OK` | Downbeat/bar-phase error = 0 beat positions (requires a shared, defined meter — not defined for cross-meter pairs, see `human_confirmations` in manifest schema §5) |
| `COND_CUE_OK` | Cue-region error = 0 ms (entry/exit lands inside an annotated acceptable region) |
| `COND_PHRASE_OK` | Phrase-boundary distance ≤ 0.5 × the local beat period |
| `COND_SECTION_OK` | Section-boundary distance ≤ 1 × the local bar period |
| `COND_TEMPO_ENVELOPE_OK` | Applied tempo-ratio deviation from 1.0 ≤ the pair's `manipulation_constraints.tempo_ratio_max_deviation` (default 12%) |
| `COND_PITCH_ENVELOPE_OK` | Pitch-shift magnitude ≤ the pair's `manipulation_constraints.max_pitch_shift_semitones` (default 3 semitones) |
| `COND_VOCAL_OK` | Vocal-overlap ratio ≤ 0.3 **and** duration ≤ 2000 ms, measured on the rendered/post-mix transition audio (never on raw source `vocal_intervals_ms`) |
| `COND_BASS_OK` | Bass-overlap proxy covers ≤ the pair's `manipulation_constraints.low_band_coactivity_ratio_ceiling` (default 50%) of the transition window |
| `COND_LOUDNESS_OK` | Momentary loudness delta ≤ 2 LU |

Where no condition cleanly applies to a pair's specific structural situation (e.g. cross-meter downbeat compatibility), the pair's `accepted_conditional` entry may add `human_confirmations` (manifest schema §5) instead of being left with no path to acceptance, or being categorically rejected on the basis of a measurement gap rather than a genuine structural fact.

**Default derivations:** `tempo_ratio_max_deviation` = 12% is set relative to SimpMusic's own shipped ±25% ceiling (P0-M1 §6), intentionally tighter. The `C5`/`COND_BASS_OK` co-activity threshold (−12 dB relative to each track's own low-band peak, sustained ≥500 ms, ≤50% of the transition window) is derived in §10.

## 8. Objective metrics

| Metric | Formula / method | Unit | Ground truth | Threshold/range | Class | Notes |
|---|---|---|---|---|---|---|
| Beat alignment error | `min(\|t_actual − t_nearest_grid_beat\|, beat_period − \|...\|)` | ms, beat-fraction | Beat timestamps | `COND_BEAT_OK`: ≤1/16 beat | `OBJECTIVE`/`PROXY` per source | |
| Downbeat/bar-phase error | Circular distance in beat positions | integer | Downbeat/bar-start annotations | `COND_DOWNBEAT_OK`: =0 | `OBJECTIVE` | `N/A` for ambiguous/cross-meter fixtures |
| Cue-region error | Distance to nearest acceptable region edge; 0 if inside | ms | Region annotations (empty array = authored "no region") | `COND_CUE_OK`: =0 | `OBJECTIVE`/`PROXY` per source | |
| Phrase-boundary distance | `min(\|t − nearest_phrase_boundary\|)` | ms | Phrase annotations | `COND_PHRASE_OK`: ≤0.5×beat period | `OBJECTIVE`/`PROXY` per source | |
| Section-boundary distance | Same method, section annotations | ms | Section annotations | `COND_SECTION_OK`: ≤1×bar period | `PROXY` | |
| Vocal overlap duration/ratio | Simultaneous rendered/post-mix vocal-band energy above audibility floor, within the window | ms, ratio | Rendered audio, informed by source `vocal_intervals_ms` | `COND_VOCAL_OK`; `C4` | `PROXY`/`OBJECTIVE` per source | Measured on rendered output — any mitigation technique (stem separation, ducking, spectral separation, cue placement) is scored by its result, not its name |
| Bass-overlap proxy | Co-occurrence of both tracks' low-band (20–150 Hz) RMS ≥ threshold, sustained ≥ minimum duration | ms, ratio | Bass activity/raw low-band energy | `COND_BASS_OK`; `C5` | `PROXY` | Also rendered-basis |
| Momentary loudness delta | `\|LUFS_momentary(t_post)−LUFS_momentary(t_pre)\|`, 400 ms window | LU | None beyond audio | `COND_LOUDNESS_OK`: ≤2 LU; `C6` | `OBJECTIVE` | |
| Short-term loudness continuity | 3 s-window loudness trend comparison | LU | None beyond audio | Scored per Lane C case | `OBJECTIVE` | |
| Transition-window loudness discontinuity | Max derivative of momentary (400 ms/100 ms hop) loudness curve vs. baseline | LU/s | None beyond audio | `C6` | `OBJECTIVE` | Momentary-basis only |
| Energy-continuity delta/slope | Pre/post RMS-energy trend slope difference | dB/s | None beyond audio | Scored per Lane C case | `PROXY` | |
| Applied tempo ratio / max deviation | Executed vs. native playback rate | ratio, % | Engine-measured | `COND_TEMPO_ENVELOPE_OK`; `C7` | `OBJECTIVE` | |
| Pitch shift | `12·log2(f_shifted/f_original)` | semitones | Engine-measured | `COND_PITCH_ENVELOPE_OK`; `C8` | `OBJECTIVE` | |
| Click/pop/discontinuity/dropout candidate flag | Waveform-discontinuity/dropout detector | count, timestamps | None beyond audio | `C9` (two-stage) | `PROXY` | Raw flag is a candidate, never confirmed alone |
| Clipping / true-peak | ITU-R BS.1770-5 true-peak | dBTP | None beyond audio | ≤−1 dBTP | `OBJECTIVE` | |
| Transition duration | Wall-clock executed transition window | ms | Engine-measured | Interpreted alongside class | `OBJECTIVE` | |
| Transition-class correctness | `observed_class` (§5.2) vs. `transition_class_policy`: (1) in `accepted_unconditional` → correct; (2) has an `accepted_conditional` entry → correct iff `conditions`/`human_confirmations` satisfied, else mismatch; (3) has a `rejected_conditional` entry → correct iff `unless_conditions` **are** satisfied, else mismatch **and** `C11`-eligible via that entry's mandatory `reason`; (4) has a `rejected` entry → always mismatch and `C11`-eligible; (5) otherwise → mismatch, weak reason, not `C11`-eligible | categorical + confusion matrix | `transition_class_policy` | `G4` | `PROXY` | Evaluated exclusively against `observed_class`, never `engine_reported_class` |

## 9. Human listening rubric

Human listening is **mandatory** and has **veto authority** over any automated PASS.

### 9.1 Scale

Anchored 1–5 (dimensions 1–15): 1 = clearly broken, 2 = poor, 3 = acceptable, 4 = good, 5 = excellent. `N/A` always valid.

### 9.2 Scored dimensions

1–15: entry-point naturalness, exit-point naturalness, beat coherence, downbeat/bar coherence, phrase coherence, section coherence, vocal handling, bass/frequency handling, energy flow, loudness continuity, tempo/stretch naturalness, pitch/key naturalness, DSP smoothness, transition-style appropriateness, overall musical intentionality.

**Dimension 16 — Preference vs. baseline**: every pair is played blinded, order-randomized, in both its candidate-system and fixed-equal-power-crossfade-baseline rendering. The listener records exactly one of `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE`. Plus an independent veto flag: `CATASTROPHIC_FAILURE_OBSERVED: yes/no + code (§10) + note`, which forces pair `FAIL` regardless of every other score.

**`human_confirmations` rubric checks (revised — R15):** when a pair's `transition_class_policy.accepted_conditional[].human_confirmations` (manifest schema §5) lists one or more `{dimension, min_score}` entries, the listener rates **every** listed dimension as part of the same blinded session; `human_all_required` (default `true`) determines whether all must clear their `min_score` (AND) or at least one (OR). `PAIR-SYN-A-010` is the worked example: `human_confirmations: [{"dimension":"beat_coherence","min_score":3},{"dimension":"downbeat_bar_coherence","min_score":3}], human_all_required: true` — both must independently score ≥3 (see the pair catalog for the full serialized JSON).

### 9.3 Procedure

Blinded/randomized, single-owner initially with a defined multi-rater upgrade path (inter-rater agreement reported per dimension once ≥2 raters exist; disagreement ≥2 points is reported as a distribution, never averaged away). Every human-rated pair records rater ID, timestamp, playback order, and blinding self-check.

## 10. Catastrophic failures

Any **confirmed** code triggers pair `FAIL`, independent of aggregate averages, and counts toward `G6`. A human veto independently triggers `FAIL`, gated as `G7`.

| Code | Definition | Threshold / detection |
|---|---|---|
| `C1_BEAT_TRAINWRECK` | Sustained audible beat drift on a beat-synced pair | Beat-alignment error > 1/8 beat for > 50% of the overlap window, BPM gap ≤ 3%. Safety-critical |
| `C2_BAR_PHASE_ERROR` | Wrong beat-in-bar on a bar-synced pair | Downbeat/bar-phase error > 0 beat positions. Safety-critical |
| `C3_WRONG_PHRASE_LOCATION` | Entry/exit far outside any acceptable region | Cue-region error exceeds a phrase/8-bar distance, for `observed_class ∈ {FULL_DJ_BLEND, SHORT_EQ_BLEND}` |
| `C4_SEVERE_VOCAL_COLLISION` | Two independently active vocal lines overlap heavily, measured on rendered audio | Vocal-overlap ratio > 60% and duration > 4 s. Safety-critical |
| `C5_SEVERE_BASS_MASKING` | Full-energy bass-on-bass collision in a short transition | Bass co-activity (≥`low_band_coactivity_threshold_db`, sustained ≥`low_band_coactivity_min_duration_ms`) covers > 50% of a window < 4000 ms |
| `C6_GROSS_LOUDNESS_DISCONTINUITY` | Audible loudness jump, momentary basis only | > 6 LU momentary jump between consecutive 100 ms-stepped measurements, or > 3 LU momentary step at a `CUT`/`GAPLESS` splice. Safety-critical |
| `C7_STRETCH_ARTIFACT` | Tempo correction produces an audible artifact | Applied deviation exceeds `tempo_ratio_max_deviation` **and** human DSP-smoothness (dim. 13) ≤2 |
| `C8_PITCH_ARTIFACT` | Pitch correction produces an audible artifact | Shift exceeds `max_pitch_shift_semitones`, or any shift paired with human pitch/key-naturalness (dim. 12) ≤2 |
| `C9_CLICK_POP_DROPOUT` | Audible discontinuity/dropout at the splice/commit boundary | Two-stage: `C9_CANDIDATE` (detector fires; logged only) → `C9_CONFIRMED` (corroborated by a deterministic dropout/underrun, or a blinded human rating dim. 13 ≤2/veto within ±250 ms). Safety-critical, confirmed form only |
| `C10_WRONG_METADATA_POISONING` | Engine's BPM/key input diverges from ground truth and measurably drives a bad decision | Input BPM off > 3 (non-half/double-time) or key off > 1 Camelot step, traceable to the resulting decision |
| `C11_FORCED_WRONG_TRANSITION_STYLE` | `observed_class` (never `engine_reported_class`) matches a categorically excluded class for the pair, corroborated by evidence | **Revised — R15**: fires when `observed_class` matches either (a) an unconditional `rejected` entry, or (b) a `rejected_conditional` entry whose `unless_conditions` are **not** satisfied by the actual rendered execution — in both cases grounded by that entry's mandatory `reason`, plus, where named, an objective metric breach or a human rating ≤2/veto on transition-style appropriateness (dim. 14) |

"Safety-critical" codes (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`, `HUMAN_VETO`) require **zero** occurrences on the Tier-1 holdout split (`G6`/`G7`, §12).

**`C5` co-activity threshold derivation:** −12 dB relative to each track's own low-band peak (≈25% of peak amplitude, a standard "clearly active" cutoff), sustained ≥500 ms (excludes brief incidental overlaps).

## 11. Anti-overfitting

The benchmark must not be EDM/4-on-the-floor-only. Coverage plan: pop, hip-hop, R&B, rock, electronic, acoustic, ballad, dynamic-tempo/live material where legally obtainable, unusual intros/outros, non-4/4 cases. Holdout pairs/categories may not be hand-tuned — any threshold/heuristic/fixture adjustment made in response to a specific holdout pair's result invalidates that holdout pair.

## 12. P0 → P1 gate

P1 (local AutoMix engine **production** implementation) remains **BLOCKED** until `G1`–`G8` all pass. This blocks the production, shipping engine only — a disposable P0-M3 benchmark-execution prototype that exists solely to produce this gate's own evidence is not itself blocked by it.

### Minimum corpus / gate sample-size plan (revised — R16)

Machine-readable source of truth: `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §2 `manifest.json.corpus_minimums`.

- Tier-1 total: **74** (`dev` 52 / `holdout` 22, sized per `G1`'s tie-robustness requirement below).
- Per-lane minimum: Lane A ≥23, Lane B ≥8, Lane C ≥8, Lane D ≥12, Lane E ≥23.
- Lane-A "clean structure" subset (`G3`): total ≥10, holdout ≥3.
- **Lane-E overall holdout (`G4`'s transition-class match-rate check — new machine-readable field, R16): `lane_e_holdout_min = 7`** (≈30% of Lane E's 23-pair total, `ceil(0.3×23)=7`).
- Lane-E "should-not-full-blend" adversarial subset (`G4`'s `C11` zero-tolerance check): total ≥8, holdout ≥3 — a **subset** of the 7 Lane-E holdout pairs above, not additive (at least 3 of Lane E's 7 required holdout pairs must be drawn from the adversarial subset).
- `G2` SimpMusic-comparison subset: 30 (`dev` 21 / `holdout` 9).
- Cross-check: proportional ~30% holdout allocation across all five lanes (A:7, B:2, C:2, D:4, E:7) sums to exactly 22, matching the overall Tier-1 holdout minimum — the named subset minimums are simultaneously achievable via one natural split, not competing requirements.

### G1 — Materially better blind human preference than fixed-duration equal-power crossfade

Recorded as `CANDIDATE_PREFERRED`/`BASELINE_PREFERRED`/`TIE` per §9.2, one outcome per distinct pair (repeated ratings of the same pair are aggregated to a single decisive/tie outcome by majority vote before entering the binomial count; an exact rater tie is itself recorded as `TIE`). Ties excluded from the win-rate ratio (`win_rate = CANDIDATE_PREFERRED/(CANDIDATE_PREFERRED+BASELINE_PREFERRED)`), reported alongside `tie_rate = TIE/n_total`; `tie_rate > 20%` → inconclusive, requiring more distinct pairs.

**Holdout tie-safety (R10, unchanged by this revision):** the holdout minimum is 22 because `22 − floor(0.20×22) = 22−4 = 18` — the smallest pool where the maximum tie count still compliant with the 20% ceiling (4 ties, 18.2%) still leaves the required 18 decisive trials.

**Threshold:** one-sided exact binomial test against null `p₀=0.5`. Combined `dev`+`holdout`: `n≥40` decisive, win rate ≥65%, `p<0.05`. Holdout alone: `n≥18` decisive (guaranteed by the 22-pair pool), win rate ≥60% (point-estimate, not independently significance-tested at this n).

**Exact binomial boundary table:**

| n | k (wins) | Win rate | Exact one-sided p-value | Passes p<0.05? |
|---|---|---|---|---|
| 40 | 26 | 65.0% | 0.0403 | Yes |
| 40 | 25 | 62.5% | 0.0769 | No |
| 18 | 11 | 61.1% | 0.2403 | No (confirms holdout-alone is a point estimate) |
| 18 | 10 | 55.6% | 0.4073 | No |

**Non-zero-tie worked example (22-pair holdout at worst-case-compliant tie count):** n=22, 4 ties (18.2%, ≤20% ceiling) → 18 decisive trials, meeting `n≥18` exactly. Contrast: the prior 18-pair design with just 1 tie (5.6%, well inside the ceiling) yields only 17 decisive trials, failing `G1`'s own requirement despite a tie rate far inside the stated threshold — the exact defect the 22-pair minimum fixes.

### G2 — Materially better quality/preference than SimpMusic-class AutoMix

Via §6.3's baseline path, mean overall-preference (dim. 15) ≥ SimpMusic-class score + 0.5, on the 30-pair `G2` subset, `n≥30` combined, `holdout n≥9`.

### G3 — Real beat/downbeat/cue/phrase-aware behavior

On the Lane-A "clean structure" subset: median beat-alignment error ≤1/16 beat and median downbeat/bar-phase error =0 for beat/bar-synced pairs; entry/exit inside an acceptable region in ≥90% of those pairs, `n≥10` combined. Also holds independently on holdout, `n≥3` — at this size, "≥90%" resolves to all 3 holdout pairs succeeding (a coarse pass/fail check at small n, disclosed explicitly rather than implying a finer-grained statistic than the sample size supports).

### G4 — Confidence-aware fallback (revised — R16)

On all Lane E pairs (`n≥23`): transition-class match rate (§8, evaluated against `observed_class`) ≥80% overall. **This must also hold independently on Lane E's holdout portion: `n≥7` (`lane_e_holdout_min`), and at `n=7`, "≥80%" is the explicit integer requirement `ceil(0.8×7)=5.6 → at least 6 of 7 correct`.**

On the Lane-E "should-not-full-blend" adversarial subset (`n≥8`): `C11` confirmed-event rate = 0%, **also independently on its holdout portion (`n≥3`, a subset of the 7 Lane-E holdout pairs above): 0 of 3.**

### G5 — Success on unseen holdout pairs (revised — R16)

Every threshold in `G1`–`G4` must hold independently on each gate's own explicitly-defined holdout component:

1. `G1`: 18 decisive holdout trials (guaranteed by the 22-pair tie-robust pool).
2. `G2`: 9 holdout pairs.
3. `G3`: 3 holdout pairs (Lane-A clean-structure subset), all 3 must succeed.
4. `G4`, check (a) — **Lane-E overall holdout transition-class match rate**: 7 holdout pairs (`lane_e_holdout_min`), at least 6 of 7 must match.
5. `G4`, check (b) — **Lane-E adversarial-subset `C11` zero-tolerance**: 3 holdout pairs (a subset of the 7 above), 0 confirmed `C11` events.

No pair-specific tuning is permitted on holdout (§11).

### G6 — Catastrophic failure rate ceiling

≤2% of the 74-pair Tier-1 corpus may trigger any confirmed `C1`–`C11` code (`floor(0.02×74)=1` pair). **Zero** confirmed safety-critical events (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`) on the 22-pair holdout subset.

### G7 — No human-veto catastrophic failures hidden by aggregate averages

`HUMAN_VETO` rate ≤1 of 74 pairs overall, **0** on the 22-pair holdout subset.

### G8 — Reproducible Tier-1 results

Re-running the full Tier-1 pipeline against the same pinned engine commit and manifest must reproduce identical objective-metric values (or a documented tolerance for any non-deterministic step); a reproduction checklist must exist and be exercised once before a `PASS` claim.

Apple Music AutoMix / djay / Offtrack / Spotify / rekordbox are **stretch references** — any benchmark report must state the observed gap against each honestly.

## 13. Stop / re-scope conditions

`RE-SCOPE` or `STOP` should be triggered if evidence, once this contract is executed against a real prototype, shows: cue/downbeat/phrase work does not materially improve over SimpMusic-class behavior (`G2`) despite implementation effort; quality remains substantially behind Offtrack/djay with no compensating advantage; real-time analysis is too expensive for target hardware; quality collapses outside a narrow genre set (§11); the confidence-aware fallback mechanism (`G4`) cannot reliably suppress catastrophic mixes even after dev-split tuning; a required capability depends on legally unavailable provider integration; or existing permissive open components already solve nearly everything this benchmark measures with no defensible improvement opportunity for a custom planner.

## 14. Scope discipline

This document and its companions are **specification/research artifacts only**. No AutoMix engine implementation and no audio fixtures are included. Disposable/benchmark-execution prototyping is explicitly in scope for a future P0-M3 task; the shipping production engine is not. Every third-party capability claim in §6 is either already-cited first-party documentation or explicitly `UNKNOWN_NEEDS_RUNTIME_PROOF` — no proprietary internals are invented. **P0-M3 is explicitly not started by this deliverable.**

## 15. Acceptance criteria check

Every Issue #4 acceptance criterion remains satisfied, unchanged in status from the PM REVIEW #2 revision. See the `HANDOFF TO PM — TAXONOMY CLOSEOUT` section of the PM-facing report for the line-by-line AC check and the R13–R16 repair-item-by-repair-item evidence trail.
