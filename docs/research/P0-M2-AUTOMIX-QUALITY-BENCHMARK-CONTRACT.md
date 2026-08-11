# P0-M2-R1 — AutoMix Quality Benchmark Contract

Status date: 2026-08-11 (PM REVIEW #4 — closeout repair)

## 0. Execution profile actually used

- **Execution agent:** Claude Code (Claude Agent SDK CLI), continuing the same session (commits `0d7ba89`, `d3c9f8b`, `3f0299a`, `3ae489a`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High (owner/PM Desktop-UI attestation, not independently introspectable — explicitly not a stop condition per Issue #4 and all four PM reviews).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **This revision addresses** `PM REVIEW #4 — CLOSEOUT REPAIR REQUIRED` (Issue #4, posted 2026-08-11T06:33:50Z), items R17–R19. R14, R15, R16 were confirmed correct by this review; R13 was confirmed "materially improved but needs one narrow correction," addressed here as R18.

## 1. Result

**PASS**

Every Issue #4 acceptance criterion is satisfied — see §15's inline matrix, which replaces the prior revision's pointer to an external handoff message (R19). `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` is now fully self-contained at this commit, with no field's type/requiredness/nullability/default/semantics dependent on reading an earlier revision (R17). `FULL_DJ_BLEND`'s native-tempo (no tempo/pitch correction) classification path no longer requires EQ automation, and now requires measured cue/phrase structural evidence in addition to sustained beat/downbeat lock, so a coincidentally-beat-aligned crossfade with poor cue placement cannot qualify while a genuinely well-placed, beat-locked, volume-only blend can (R18).

## 2. Purpose

Define the benchmark contract deciding whether AutoMix is musically better than naive crossfade/BPM-key-only mixing, and whether P1 is allowed to start. This document, `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`, and `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md` are the full deliverable set. No AutoMix engine code, no audio files. P0-M3 may build disposable, non-production benchmark-execution prototypes to actually run this contract; only the shipping production engine is blocked pending the gate.

## 3. Core benchmark principle

**BPM/key compatibility is never sufficient evidence of AutoMix quality**, per `docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §8–§10: the pinned SimpMusic baseline is `TEMPO_AWARE` with working Camelot key-compatibility scoring, yet has zero beat-timestamp, downbeat, phrase, section, or content-activity awareness, and its incoming-track start position is unconditionally `0` regardless of the outgoing track's phase. This benchmark must detect failures in cue-point choice, beat phase, downbeat/bar alignment, phrase alignment, section-aware entry/exit, vocal collision, bass/percussion masking, energy trajectory, loudness continuity, tempo-stretch artifacts, pitch-shift artifacts, clicks/pops/discontinuities, transition-style appropriateness, and confidence/fallback behavior.

Symmetrically, the benchmark must not punish an engine for succeeding at a pair that only looks adversarial on paper, must not confuse "this benchmark cannot currently measure success here" with "success is impossible," must not classify a transition's style by which DSP technique happened to be used rather than by its observable musical outcome, and must not treat the mere absence of measured overlap as proof of a seamless join. The specific subject of this revision: **the benchmark must not require a specific DSP ingredient (EQ automation) merely to recognize a genuinely well-executed native-tempo DJ blend, while still refusing to reward a transition that merely coincides with a shared BPM** (R18).

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

## 5. Transition-Class Taxonomy

**Binding, operational definitions**, owned by the benchmark runner via observable, measured evidence — never by a candidate engine's self-reported label.

### 5.1 Class definitions

| Class | Overlap | Beat/downbeat sync | Duration | Automation | Cue-point selection |
|---|---|---|---|---|---|
| `GAPLESS` | Zero overlap **and** zero (sample-contiguous, within epsilon) gap | N/A | 0 ms by definition | None | N/A — natural boundaries both sides |
| `NO_SPECIAL_TRANSITION` | Zero overlap; gap may be zero **or** a measurable positive silence | N/A | Same as `GAPLESS` at the processing level | None | N/A — natural boundaries both sides |
| `CUT` | Zero overlap; gap may be zero or positive | N/A | Same | None | Yes — at least one boundary is *not* the fixture's own natural/authored boundary |
| `SIMPLE_CROSSFADE` | Nonzero | Not required for the label | Not hardcoded | Volume/gain only | Yes |
| `SHORT_EQ_BLEND` | Nonzero | Not required for the label | Not hardcoded | Volume/gain + EQ/filter; not qualifying for `FULL_DJ_BLEND`'s evidence bar | Yes |
| `FULL_DJ_BLEND` | Nonzero | **Contractual expectation of the label** (§5.2 rule 3), established by **either** tempo/pitch automation **or** demonstrated sustained beat/downbeat lock plus cue/phrase structural evidence — **EQ automation is never required for either path** (R18) | Not hardcoded | Volume/gain always; EQ optional; tempo/pitch optional | Yes, expected |

**R18 fix, stated plainly:** the prior taxonomy's no-correction path required `has_eq_automation=true AND has_sustained_beat_lock=true`, which still tied `FULL_DJ_BLEND` to one DSP technique (EQ) and could be satisfied by beat lock alone even when the actual entry/exit placement was musically poor. `FULL_DJ_BLEND` is now earned by **either** (a) tempo/pitch automation being present — the label does not require it to *succeed*, quality is scored separately via `COND_TEMPO_ENVELOPE_OK`/`C7` — **or** (b) demonstrated sustained beat/downbeat lock **plus** measured cue/phrase/section structural evidence (§5.3), with **EQ automation not required by either path**. A bare volume-only fade that merely shares a BPM, or briefly/coincidentally touches the beat grid, does **not** qualify (§5.2 rule 3b); nor does a beat-locked blend landing at a poor cue/phrase point (§5.2 rule 3e).

Duration is deliberately never used as a hard classification threshold anywhere in this table.

### 5.2 Classification decision procedure (deterministic, runner-applied)

Given a transition render record (manifest schema §9):

1. Measure `overlap_ms` and, if `overlap_ms` is at or below the epsilon (default 20 ms), measure `inter_track_gap_ms` (**mandatory** in that branch — a missing value is never defaulted to zero).
2. **If `overlap_ms ≤ epsilon`:**
   a. `inter_track_gap_ms` missing/`null` → `observed_class = UNCLASSIFIED_ANOMALY`.
   b. `inter_track_gap_ms ≤ epsilon` (sample-contiguous join): measure `outgoing_used_natural_full_duration` and `incoming_used_natural_start`.
      - Both `true` **and** `is_continuous_work = true` → `GAPLESS`.
      - Both `true` **and** `is_continuous_work = false` → `NO_SPECIAL_TRANSITION`.
      - Not both `true` → `CUT`.
   c. `inter_track_gap_ms > epsilon` (a real, measurable, audible gap): **`GAPLESS` is never assigned in this branch**, regardless of `is_continuous_work` or boundary naturalness.
      - Both boundaries natural → `NO_SPECIAL_TRANSITION`.
      - Not both natural → `CUT`.
3. **If `overlap_ms > epsilon`:**
   a. `has_volume_automation = false` → `observed_class = UNCLASSIFIED_ANOMALY`.
   b. `has_eq_automation = false` **and** `has_tempo_pitch_automation = false` **and** `has_native_tempo_structural_evidence = false` (§5.3) → `SIMPLE_CROSSFADE` — the ordinary crossfade case, including one that happens to share a BPM without demonstrating sustained structural synchronization.
   c. `has_tempo_pitch_automation = true` → `FULL_DJ_BLEND` (independently sufficient, regardless of `has_eq_automation` or `has_native_tempo_structural_evidence` — execution quality is scored separately by `COND_TEMPO_ENVELOPE_OK`/`COND_PITCH_ENVELOPE_OK`/`C7`/`C8`, never by the classification step).
   d. `has_tempo_pitch_automation = false` **and** `has_native_tempo_structural_evidence = true` → `FULL_DJ_BLEND` (**R18 fix** — the no-correction/native-tempo path. `has_eq_automation` is **not** consulted here: a volume-only transition qualifies exactly as readily as an EQ-automated one, provided the structural evidence bar is met).
   e. `has_tempo_pitch_automation = false` **and** `has_native_tempo_structural_evidence = false` **and** `has_eq_automation = true` → `SHORT_EQ_BLEND` — genuine EQ processing was applied, but either sustained beat lock was never achieved, or it was achieved with poor cue/phrase placement, so the "full" bar is not met.
4. `class_label_mismatch = (engine_reported_class != observed_class)`, diagnostic only.

`engine_reported_class` is never consulted in steps 1–3. Rule ordering matters: rule 3b is evaluated first and only fires when `has_native_tempo_structural_evidence` is already known to be `false`, so a pair that turns out to have strong structural evidence never gets trapped in `SIMPLE_CROSSFADE` merely for lacking EQ/tempo automation.

### 5.3 Native-tempo structural evidence — classification evidence (R13, revised R18)

Two independent evidence dimensions jointly establish `has_native_tempo_structural_evidence` (manifest schema §9), which governs the no-correction `FULL_DJ_BLEND` path (rule 3d above):

**(a) Sustained beat/downbeat lock.** `sustained_beat_lock_ratio`: using each track's own beat timestamps mapped through its actually-applied playback-rate curve (native/constant when `has_tempo_pitch_automation=false`), compute — for beat-grid instants within the overlap window — the fraction where **both** instantaneous beat-alignment error ≤1/16 beat (`COND_BEAT_OK`'s own threshold) **and** downbeat-phase error =0, simultaneously. `has_sustained_beat_lock = true` iff `sustained_beat_lock_ratio ≥0.8` **and** `overlap_ms ≥ 4×local_bar_period_ms` (a duration floor distinguishing sustained lock from a single lucky instant). Both `null` when reliable beat ground truth is unavailable for either track — never imputed.

**(b) Cue/phrase/section structural placement (new — R18).** Beat lock alone can be coincidental (e.g. two tracks that happen to share tempo and phase for a stretch, entered/exited at a musically arbitrary point). Two further signals are required, each evaluated **only where the relevant ground truth is reliably annotated** (a "where available" evidence bar, permissive when no ground truth exists, but never satisfied merely by the *absence* of contradicting evidence when ground truth *does* exist):

- `cue_placement_ok`: for whichever side (outgoing exit / incoming entry) has reliable `acceptable_exit_regions_ms`/`acceptable_entry_regions_ms` ground truth, the actual rendered entry/exit point must land inside the annotated region (`COND_CUE_OK` satisfied for that side). `true` by default only when *neither* side has reliable region ground truth to check against; `false` whenever ground truth exists for a side and the render misses it.
- `phrase_section_alignment_ok`: for whichever of `phrase_boundaries_ms`/`section_boundaries` is reliably annotated, the render must satisfy the corresponding `COND_PHRASE_OK`/`COND_SECTION_OK`. `true` by default only when neither is reliably annotated; `false` whenever annotated and unmet.

`has_native_tempo_structural_evidence = has_sustained_beat_lock AND cue_placement_ok AND phrase_section_alignment_ok`, where a `null` (unresolved) `has_sustained_beat_lock` makes the composite `false` — missing beat evidence can never grant the no-correction path.

**Data classification:** `OBJECTIVE` when computed against `SYNTHETIC_EXACT`/`MANUAL` ground truth for the relevant dimension, `PROXY` when computed against `MODEL_ESTIMATE` ground truth, consistent with every other metric's source-dependent tagging in §8.

### 5.4 Worked classification examples

**`FULL_DJ_BLEND` no-correction-path examples (R18 REQUIRED VALIDATION):**

| # | Scenario | Key measured signals | `observed_class` | Rule |
|---|---|---|---|---|
| 1 | Native tempo, **volume-only**, sustained beat/downbeat lock **and** correct cue/phrase placement | `overlap_ms=18000`, `has_volume_automation=true`, `has_eq_automation=false`, `has_tempo_pitch_automation=false`, `sustained_beat_lock_ratio=0.94` (bar period 2000 ms at 120 BPM; window ≥4×2000=8000 ms) → `has_sustained_beat_lock=true`; `cue_placement_ok=true`; `phrase_section_alignment_ok=true` → `has_native_tempo_structural_evidence=true` | **`FULL_DJ_BLEND`** | Rule 3d — proves EQ is not required |
| 2 | Native tempo, **EQ automation**, beat-locked **but bad cue/phrase placement** | `overlap_ms=16000`, `has_volume_automation=true`, `has_eq_automation=true`, `has_tempo_pitch_automation=false`, `sustained_beat_lock_ratio=0.85` → `has_sustained_beat_lock=true`; rendered exit point measured **outside** the annotated `acceptable_exit_regions_ms` → `cue_placement_ok=false` → `has_native_tempo_structural_evidence=false` | **`SHORT_EQ_BLEND`** (not `FULL_DJ_BLEND`) | Rule 3e — proves beat lock alone (even with EQ present) does not automatically qualify; bad measured placement blocks it |
| 3 | Time-stretched DJ blend (tracks natively 8% apart) | `overlap_ms=25000`, `has_volume_automation=true`, `has_eq_automation=true`, `has_tempo_pitch_automation=true` (applied ratio within `tempo_ratio_max_deviation`) | **`FULL_DJ_BLEND`** | Rule 3c — tempo/pitch automation alone is sufficient; artifact/deviation quality scored separately by `COND_TEMPO_ENVELOPE_OK`/`C7`, never by this classification step |
| 4 | Ordinary equal-power crossfade, same BPM, **no demonstrated structural synchronization** | `overlap_ms=6000`, `has_volume_automation=true`, `has_eq_automation=false`, `has_tempo_pitch_automation=false`, `sustained_beat_lock_ratio=0.40` (tracks not actually phase-locked despite matching BPM) → `has_sustained_beat_lock=false` → `has_native_tempo_structural_evidence=false` | **`SIMPLE_CROSSFADE`** | Rule 3b — proves same-BPM alone cannot establish the native-tempo path |
| 5 *(bonus)* | Native tempo, EQ automation, **beat lock never achieved at all** | `overlap_ms=14000`, `has_volume_automation=true`, `has_eq_automation=true`, `has_tempo_pitch_automation=false`, `sustained_beat_lock_ratio=0.30` → `has_sustained_beat_lock=false` → `has_native_tempo_structural_evidence=false` | **`SHORT_EQ_BLEND`** | Rule 3e — same outcome as #2 via a different underlying evidence failure, showing rule 3e fires whenever *either* sub-condition of `has_native_tempo_structural_evidence` fails, not only the cue/phrase one |

Rows 1 and 3 both classify `FULL_DJ_BLEND` via two independent paths (no-correction structural evidence vs. tempo/pitch automation) — proving neither is individually mandatory. Row 2 proves sustained beat lock alone is insufficient once cue/phrase evidence is measurably bad. Row 4 proves shared BPM alone, without demonstrated sustained lock, cannot establish the native-tempo path. Row 5 proves the same negative result can arise from the beat-lock sub-condition failing instead of the cue/phrase sub-condition.

**Zero-overlap / `GAPLESS` examples:**

| # | Scenario | Key measured signals | `observed_class` | Rule |
|---|---|---|---|---|
| D | Natural boundary, `gap_ms=0`, `is_continuous_work=true` | `overlap_ms=0`, `inter_track_gap_ms=0`, both natural boundaries | **`GAPLESS`** | Rule 2b, continuous-work branch |
| D' | Same as D but `is_continuous_work=false` | Same measured signals, different annotation | **`NO_SPECIAL_TRANSITION`** (not `GAPLESS`) | Rule 2b, non-continuous branch |
| E | Natural boundary, positive audible gap (1500 ms) | `overlap_ms=0`, `inter_track_gap_ms=1500` (>20 ms epsilon), both natural | **`NO_SPECIAL_TRANSITION`** (never `GAPLESS`) | Rule 2c |

### 5.5 Stem/source-separation and other techniques — diagnostic only, never gating

`stem_separation_applied` (manifest schema §9) records whether the system under test applied stem/source-separation or targeted attenuation, purely as **diagnostic metadata**. It is never referenced by any `transition_class_policy` entry or classification rule. Where a pair's acceptance of a class depends on an audible outcome achievable by more than one technique (e.g. avoiding a vocal collision via stem separation, dynamic ducking, spectral separation, or alternate cue-point handling), the policy is written in terms of the **outcome condition** (e.g. `COND_VOCAL_OK`, measured on rendered audio regardless of mechanism) via `rejected_conditional` or `accepted_conditional` (manifest schema §6) — never a named technology. See `PAIR-SYN-E-007` in the pair catalog for the worked example.

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

Named, reusable objective conditions referenced by `transition_class_policy` entries (manifest schema §6). These govern **acceptance quality** of an already-classified transition and, since R18, also feed §5.3's classification-evidence computation; they remain distinct from — and never substitute for — the render-record signals that determine *which class was rendered in the first place*.

| Condition ID | Definition |
|---|---|
| `COND_BEAT_OK` | Beat-alignment error (beat-fraction) ≤1/16 (6.25%) at the chosen anchor point |
| `COND_DOWNBEAT_OK` | Downbeat/bar-phase error =0 beat positions (requires a shared, defined meter — not defined for cross-meter pairs, see `human_confirmations` in manifest schema §6) |
| `COND_CUE_OK` | Cue-region error =0 ms (entry/exit lands inside an annotated acceptable region) |
| `COND_PHRASE_OK` | Phrase-boundary distance ≤0.5×the local beat period |
| `COND_SECTION_OK` | Section-boundary distance ≤1×the local bar period |
| `COND_TEMPO_ENVELOPE_OK` | Applied tempo-ratio deviation from 1.0 ≤ the pair's `manipulation_constraints.tempo_ratio_max_deviation` (default 12%) |
| `COND_PITCH_ENVELOPE_OK` | Pitch-shift magnitude ≤ the pair's `manipulation_constraints.max_pitch_shift_semitones` (default 3 semitones) |
| `COND_VOCAL_OK` | Vocal-overlap ratio ≤0.3 **and** duration ≤2000 ms, measured on the rendered/post-mix transition audio (never on raw source `vocal_intervals_ms`) |
| `COND_BASS_OK` | Bass-overlap proxy covers ≤ the pair's `manipulation_constraints.low_band_coactivity_ratio_ceiling` (default 50%) of the transition window |
| `COND_LOUDNESS_OK` | Momentary loudness delta ≤2 LU |

Where no condition cleanly applies to a pair's specific structural situation (e.g. cross-meter downbeat compatibility), the pair's `accepted_conditional` entry may add `human_confirmations` (manifest schema §6) instead of being left with no path to acceptance, or being categorically rejected on the basis of a measurement gap rather than a genuine structural fact.

**Default derivations:** `tempo_ratio_max_deviation`=12% is set relative to SimpMusic's own shipped ±25% ceiling (P0-M1 §6), intentionally tighter. The `C5`/`COND_BASS_OK` co-activity threshold (−12 dB relative to each track's own low-band peak, sustained ≥500 ms, ≤50% of the transition window) is derived in §10.

## 8. Objective metrics

| Metric | Formula / method | Unit | Ground truth | Threshold/range | Class | Notes |
|---|---|---|---|---|---|---|
| Beat alignment error | `min(\|t_actual − t_nearest_grid_beat\|, beat_period − \|...\|)` | ms, beat-fraction | Beat timestamps | `COND_BEAT_OK`: ≤1/16 beat | `OBJECTIVE`/`PROXY` per source | Also feeds `sustained_beat_lock_ratio` (§5.3) |
| Downbeat/bar-phase error | Circular distance in beat positions | integer | Downbeat/bar-start annotations | `COND_DOWNBEAT_OK`: =0 | `OBJECTIVE` | `N/A` for ambiguous/cross-meter fixtures |
| Cue-region error | Distance to nearest acceptable region edge; 0 if inside | ms | Region annotations (empty array = authored "no region") | `COND_CUE_OK`: =0 | `OBJECTIVE`/`PROXY` per source | Also feeds `cue_placement_ok` (§5.3) |
| Phrase-boundary distance | `min(\|t − nearest_phrase_boundary\|)` | ms | Phrase annotations | `COND_PHRASE_OK`: ≤0.5×beat period | `OBJECTIVE`/`PROXY` per source | Also feeds `phrase_section_alignment_ok` (§5.3) |
| Section-boundary distance | Same method, section annotations | ms | Section annotations | `COND_SECTION_OK`: ≤1×bar period | `PROXY` | Also feeds `phrase_section_alignment_ok` (§5.3) |
| Vocal overlap duration/ratio | Simultaneous rendered/post-mix vocal-band energy above audibility floor, within the window | ms, ratio | Rendered audio, informed by source `vocal_intervals_ms` | `COND_VOCAL_OK`; `C4` | `PROXY`/`OBJECTIVE` per source | Rendered-basis — any mitigation technique is scored by its result |
| Bass-overlap proxy | Co-occurrence of both tracks' low-band (20–150 Hz) RMS ≥threshold, sustained ≥minimum duration | ms, ratio | Bass activity/raw low-band energy | `COND_BASS_OK`; `C5` | `PROXY` | Also rendered-basis |
| Momentary loudness delta | `\|LUFS_momentary(t_post)−LUFS_momentary(t_pre)\|`, 400 ms window | LU | None beyond audio | `COND_LOUDNESS_OK`: ≤2 LU; `C6` | `OBJECTIVE` | |
| Short-term loudness continuity | 3 s-window loudness trend comparison | LU | None beyond audio | Scored per Lane C case | `OBJECTIVE` | |
| Transition-window loudness discontinuity | Max derivative of momentary (400 ms/100 ms hop) loudness curve vs. baseline | LU/s | None beyond audio | `C6` | `OBJECTIVE` | Momentary-basis only, never "short-term" |
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

**`human_confirmations` rubric checks:** when a pair's `transition_class_policy.accepted_conditional[].human_confirmations` (manifest schema §6) lists one or more `{dimension, min_score}` entries, the listener rates **every** listed dimension as part of the same blinded session; `human_all_required` (default `true`) determines whether all must clear their `min_score` (AND) or at least one (OR). `PAIR-SYN-A-010` is the worked example: `human_confirmations: [{"dimension":"beat_coherence","min_score":3},{"dimension":"downbeat_bar_coherence","min_score":3}], human_all_required: true` (see the pair catalog for the literal JSON).

### 9.3 Procedure

Blinded/randomized, single-owner initially with a defined multi-rater upgrade path (inter-rater agreement reported per dimension once ≥2 raters exist; disagreement ≥2 points is reported as a distribution, never averaged away). Every human-rated pair records rater ID, timestamp, playback order, and blinding self-check.

## 10. Catastrophic failures

Any **confirmed** code triggers pair `FAIL`, independent of aggregate averages, and counts toward `G6`. A human veto independently triggers `FAIL`, gated as `G7`.

| Code | Definition | Threshold / detection |
|---|---|---|
| `C1_BEAT_TRAINWRECK` | Sustained audible beat drift on a beat-synced pair | Beat-alignment error > 1/8 beat for > 50% of the overlap window, BPM gap ≤3%. Safety-critical |
| `C2_BAR_PHASE_ERROR` | Wrong beat-in-bar on a bar-synced pair | Downbeat/bar-phase error > 0 beat positions. Safety-critical |
| `C3_WRONG_PHRASE_LOCATION` | Entry/exit far outside any acceptable region | Cue-region error exceeds a phrase/8-bar distance, for `observed_class ∈ {FULL_DJ_BLEND, SHORT_EQ_BLEND}` |
| `C4_SEVERE_VOCAL_COLLISION` | Two independently active vocal lines overlap heavily, measured on rendered audio | Vocal-overlap ratio > 60% and duration > 4 s. Safety-critical |
| `C5_SEVERE_BASS_MASKING` | Full-energy bass-on-bass collision in a short transition | Bass co-activity (≥`low_band_coactivity_threshold_db`, sustained ≥`low_band_coactivity_min_duration_ms`) covers > 50% of a window < 4000 ms |
| `C6_GROSS_LOUDNESS_DISCONTINUITY` | Audible loudness jump, momentary basis only | > 6 LU momentary jump between consecutive 100 ms-stepped measurements, or > 3 LU momentary step at a `CUT`/`GAPLESS` splice. Safety-critical |
| `C7_STRETCH_ARTIFACT` | Tempo correction produces an audible artifact | Applied deviation exceeds `tempo_ratio_max_deviation` **and** human DSP-smoothness (dim. 13) ≤2 |
| `C8_PITCH_ARTIFACT` | Pitch correction produces an audible artifact | Shift exceeds `max_pitch_shift_semitones`, or any shift paired with human pitch/key-naturalness (dim. 12) ≤2 |
| `C9_CLICK_POP_DROPOUT` | Audible discontinuity/dropout at the splice/commit boundary | Two-stage: `C9_CANDIDATE` (detector fires; logged only) → `C9_CONFIRMED` (corroborated by a deterministic dropout/underrun, or a blinded human rating dim. 13 ≤2/veto within ±250 ms). Safety-critical, confirmed form only |
| `C10_WRONG_METADATA_POISONING` | Engine's BPM/key input diverges from ground truth and measurably drives a bad decision | Input BPM off >3 (non-half/double-time) or key off >1 Camelot step, traceable to the resulting decision |
| `C11_FORCED_WRONG_TRANSITION_STYLE` | `observed_class` (never `engine_reported_class`) matches a categorically excluded class for the pair, corroborated by evidence | Fires when `observed_class` matches either (a) an unconditional `rejected` entry, or (b) a `rejected_conditional` entry whose `unless_conditions` are **not** satisfied — in both cases grounded by that entry's mandatory `reason`, plus, where named, an objective metric breach or a human rating ≤2/veto on transition-style appropriateness (dim. 14) |

"Safety-critical" codes (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`, `HUMAN_VETO`) require **zero** occurrences on the Tier-1 holdout split (`G6`/`G7`, §12).

**`C5` co-activity threshold derivation:** −12 dB relative to each track's own low-band peak (≈25% of peak amplitude, a standard "clearly active" cutoff), sustained ≥500 ms (excludes brief incidental overlaps).

## 11. Anti-overfitting

The benchmark must not be EDM/4-on-the-floor-only. Coverage plan: pop, hip-hop, R&B, rock, electronic, acoustic, ballad, dynamic-tempo/live material where legally obtainable, unusual intros/outros, non-4/4 cases. Holdout pairs/categories may not be hand-tuned — any threshold/heuristic/fixture adjustment made in response to a specific holdout pair's result invalidates that holdout pair.

## 12. P0 → P1 gate

P1 (local AutoMix engine **production** implementation) remains **BLOCKED** until `G1`–`G8` all pass. This blocks the production, shipping engine only — a disposable P0-M3 benchmark-execution prototype that exists solely to produce this gate's own evidence is not itself blocked by it.

### Minimum corpus / gate sample-size plan

Machine-readable source of truth: `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §2 `manifest.json.corpus_minimums`.

- Tier-1 total: **74** (`dev` 52 / `holdout` 22, sized per `G1`'s tie-robustness requirement below).
- Per-lane minimum: Lane A ≥23, Lane B ≥8, Lane C ≥8, Lane D ≥12, Lane E ≥23.
- Lane-A "clean structure" subset (`G3`): total ≥10, holdout ≥3.
- Lane-E overall holdout (`G4`'s transition-class match-rate check): `lane_e_holdout_min = 7` (≈30% of Lane E's 23-pair total).
- Lane-E "should-not-full-blend" adversarial subset (`G4`'s `C11` zero-tolerance check): total ≥8, holdout ≥3 — a **subset** of the 7 Lane-E holdout pairs above, not additive.
- `G2` SimpMusic-comparison subset: 30 (`dev` 21 / `holdout` 9).
- Cross-check: proportional ~30% holdout allocation across all five lanes (A:7, B:2, C:2, D:4, E:7) sums to exactly 22, matching the overall Tier-1 holdout minimum.

### G1 — Materially better blind human preference than fixed-duration equal-power crossfade

Recorded as `CANDIDATE_PREFERRED`/`BASELINE_PREFERRED`/`TIE` per §9.2, one outcome per distinct pair (repeated ratings of the same pair are aggregated to a single decisive/tie outcome by majority vote before entering the binomial count). Ties excluded from the win-rate ratio, `tie_rate > 20%` → inconclusive. Holdout tie-safety: 22-pair pool guarantees `≥18` decisive trials even at the maximum tie count compliant with the 20% ceiling (`22−floor(0.20×22)=18`). Combined `dev`+`holdout`: `n≥40` decisive, win rate ≥65%, `p<0.05` (exact binomial, e.g. n=40/k=26 → p=0.0403). Holdout alone: `n≥18` decisive, win rate ≥60% (point-estimate, not independently significance-tested at this n).

### G2 — Materially better quality/preference than SimpMusic-class AutoMix

Via §6.3's baseline path, mean overall-preference (dim. 15) ≥ SimpMusic-class score +0.5, on the 30-pair `G2` subset, `n≥30` combined, `holdout n≥9`.

### G3 — Real beat/downbeat/cue/phrase-aware behavior

On the Lane-A "clean structure" subset: median beat-alignment error ≤1/16 beat and median downbeat/bar-phase error =0 for beat/bar-synced pairs; entry/exit inside an acceptable region in ≥90% of those pairs, `n≥10` combined, holdout `n≥3` (all 3 must succeed at this size).

### G4 — Confidence-aware fallback

On all Lane E pairs (`n≥23`): transition-class match rate (§8, against `observed_class`) ≥80% overall, **also independently on holdout `n≥7` (`lane_e_holdout_min`), stated as ≥6 of 7 correct** (`ceil(0.8×7)=5.6→6`). On the Lane-E adversarial subset (`n≥8`): `C11` confirmed-event rate =0%, **also independently on its holdout `n≥3` (a subset of the 7 above): 0 of 3.**

### G5 — Success on unseen holdout pairs

Every threshold in `G1`–`G4` must hold independently on each gate's own explicitly-defined holdout component: `G1` 18 decisive trials; `G2` 9 pairs; `G3` 3 pairs (all must succeed); `G4` check (a) 7 pairs (≥6 must match) and check (b) 3 pairs (0 confirmed `C11`, a subset of the 7). No pair-specific tuning is permitted on holdout (§11).

### G6 — Catastrophic failure rate ceiling

≤2% of the 74-pair Tier-1 corpus may trigger any confirmed `C1`–`C11` code (`floor(0.02×74)=1` pair). **Zero** confirmed safety-critical events on the 22-pair holdout subset.

### G7 — No human-veto catastrophic failures hidden by aggregate averages

`HUMAN_VETO` rate ≤1 of 74 pairs overall, **0** on the 22-pair holdout subset.

### G8 — Reproducible Tier-1 results

Re-running the full Tier-1 pipeline against the same pinned engine commit and manifest must reproduce identical objective-metric values (or a documented tolerance for any non-deterministic step); a reproduction checklist must exist and be exercised once before a `PASS` claim.

Apple Music AutoMix / djay / Offtrack / Spotify / rekordbox are **stretch references** — any benchmark report must state the observed gap against each honestly.

## 13. Stop / re-scope conditions

`RE-SCOPE` or `STOP` should be triggered if evidence, once this contract is executed against a real prototype, shows: cue/downbeat/phrase work does not materially improve over SimpMusic-class behavior (`G2`) despite implementation effort; quality remains substantially behind Offtrack/djay with no compensating advantage; real-time analysis is too expensive for target hardware; quality collapses outside a narrow genre set (§11); the confidence-aware fallback mechanism (`G4`) cannot reliably suppress catastrophic mixes even after dev-split tuning; a required capability depends on legally unavailable provider integration; or existing permissive open components already solve nearly everything this benchmark measures with no defensible improvement opportunity for a custom planner.

## 14. Scope discipline

This document and its companions are **specification/research artifacts only**. No AutoMix engine implementation and no audio fixtures are included. Disposable/benchmark-execution prototyping is explicitly in scope for a future P0-M3 task; the shipping production engine is not. Every third-party capability claim in §6 is either already-cited first-party documentation or explicitly `UNKNOWN_NEEDS_RUNTIME_PROOF` — no proprietary internals are invented. **P0-M3 is explicitly not started by this deliverable.**

## 15. Acceptance criteria matrix (R19 — inline, replaces the prior pointer to an external handoff message)

Every row is independently verifiable by reading this repository at the current commit; none require chat history or a prior PM handoff message.

| # | Acceptance criterion (Issue #4) | Result | Current evidence (this repository, this commit) |
|---|---|---|---|
| 1 | BPM-aware explicitly distinguished from beat/downbeat/phrase/cue/content-aware behavior | PASS | §3.1 terminology gate table |
| 2 | Adversarial BPM/key-only failure cases exist | PASS | §4.1–§4.5 lane case tables; `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md` (31 concrete pairs, e.g. `PAIR-SYN-A-001`–`A-003`, `PAIR-SYN-D-001`–`D-008`) |
| 3 | Objective/proxy/human-only metrics defined with units and limitations | PASS | §8 objective metrics table (unit + ground truth + threshold + class column per row) |
| 4 | Human listening rubric has anchored scoring and final veto | PASS | §9.1 anchored 1–5 scale; §9.2 veto flag forcing `FAIL` regardless of other scores |
| 5 | Catastrophic failures are defined | PASS | §10, `C1`–`C11` with thresholds and safety-critical designation |
| 6 | Fallback/no-transition behavior is benchmarked | PASS | §4.5 Lane E; §5.1 `GAPLESS`/`CUT`/`NO_SPECIAL_TRANSITION` definitions; catalog `PAIR-SYN-E-001`–`E-008` |
| 7 | Tier-1 corpus is license-safe/reproducible | PASS | Manifest schema §3 (`provenance` restricted to `SYNTHETIC`/`OWNER_CREATED`/`PUBLIC_DOMAIN`/`CC0`/`PERMISSIVE_OTHER`, mandatory `checksum`/`license`); §12 `G8` reproducibility gate |
| 8 | Tier-2 stores references only | PASS | Manifest schema §5 (Tier-2 pair object has no `local_path`/`checksum`/audio field of any kind) |
| 9 | Tuning and holdout are separated | PASS | Manifest schema §2 `split_assignment_policy` (fixed-at-creation, never reassigned by results); §11 anti-overfitting; §12 `G5` |
| 10 | Anti-overfitting beyond EDM/4-4 exists | PASS | §11 coverage plan |
| 11 | P1 gate has explicit thresholds | PASS | §12, `G1`–`G8`, every threshold stated as an exact number/percentage/integer |
| 12 | Stop/re-scope conditions are explicit | PASS | §13 |
| 13 | Proprietary-system comparison limitations are classified | PASS | §6.1 comparability-class enum; §6.2 per-system classification, including `UNKNOWN_NEEDS_RUNTIME_PROOF` flags |
| 14 | No production implementation is added | PASS | §2/§14 scope discipline; no engine source files exist anywhere in this repository at this commit — the only P0-M2 artifacts are the three `docs/research/P0-M2-*.md` files |
| 15 | No protected audio, credentials, cookies, tokens, or secrets are committed | PASS | §14; every commit in this task's history is a docs-only diff (verified via `git diff --stat` before each push) touching only the three `docs/research/P0-M2-*.md` files |
