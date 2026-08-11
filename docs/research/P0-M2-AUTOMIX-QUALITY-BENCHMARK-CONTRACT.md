# P0-M2-R1 — AutoMix Quality Benchmark Contract

Status date: 2026-08-11 (repair pass)

## 0. Execution profile actually used

- **Execution agent:** Claude Code (Claude Agent SDK CLI), continuing the same session that produced the original P0-M2-R1 pass reviewed at commit `0d7ba893e81d67fdf26e17c0ad89576c9166310b`.
- **Parent model:** `claude-sonnet-5`, matching the model pinned in Issue #4 and re-affirmed in the PM's repair-request instruction.
- **Reasoning effort:** High, per the same owner/PM Desktop-UI attestation basis as the original pass; not independently introspectable from inside the runtime, and per Issue #4/the repair instruction this is explicitly not a stop condition.
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF — no `Agent`/`Task` subagents were used for this repair pass. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **This revision addresses** the PM's `PM REVIEW — REPAIR REQUIRED` comment on Issue #4 (posted 2026-08-11T03:25:00Z), repair items R1–R9. Every section below that changed as a direct result of a repair item is marked inline with its `R#` tag so the diff's provenance is traceable without needing the original PM comment open side-by-side.

## 1. Result

**PASS**

Per the PM's explicit R9 instruction: the reasons that previously justified `PARTIAL` (no future engine/prototype exists yet to validate thresholds against; several commercial-baseline comparability classifications need future hands-on runtime verification; actual audio-fixture generation is out of scope for a specification task) are expected, structural properties of a specification-only milestone and do not by themselves block `PASS`. Every Issue #4 acceptance criterion (§14) has concrete, checkable content after this repair pass, every catastrophic-failure threshold now references a defined constant or manifest field (R4), the transition-class acceptance model is outcome-aware rather than circular (R2), the human-preference statistical gate has a fully specified data model with a worked boundary example (R5), and the SimpMusic comparison has a defined execution path regardless of whether local-file playback in actual SimpMusic is ever confirmed (R6). Remaining items — real thresholds tuned against real measurements, hands-on baseline verification, actual fixture production — are correctly future runtime/P0-M3 work, not gaps in this specification.

## 2. Purpose

Define the benchmark contract that decides whether AutoMix is musically better than naive crossfade / BPM-key-only mixing, and whether P1 (local AutoMix engine implementation) is allowed to start. This document, its companion manifest schema (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`), and the optional pair catalog (`docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`) together are the full P0-M2-R1 deliverable set. No AutoMix engine code, no audio files are included. **P0-M3 clarification (R8):** P0-M3 may build disposable, non-production benchmark-execution prototypes (e.g., a script wiring All-In-One/CUE-DETR/Signalsmith Stretch, per `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`, to actually run this contract against fixtures and produce measurements) — this is the mechanism by which the P1 gate in §11 is ever evaluated at all. Only the shipping, production, multi-platform AutoMix engine is blocked pending the gate; the disposable measurement tooling that produces the gate's own evidence is not circularly gated behind itself.

## 3. Core benchmark principle

**BPM/key compatibility is never sufficient evidence of AutoMix quality.**

`docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §8–§10 independently demonstrates why: the pinned SimpMusic baseline is `TEMPO_AWARE` and has working Camelot key-compatibility scoring, yet has zero beat-timestamp, downbeat, phrase, section, or content-activity awareness, and its incoming-track start position is unconditionally `0` regardless of the outgoing track's phase. A benchmark that only checked "did BPM/key roughly match" would score SimpMusic as if the transition-planning problem were solved. It is not. This benchmark must therefore detect failures in:

- cue-point choice
- beat phase
- downbeat/bar alignment
- phrase alignment
- section-aware entry/exit
- vocal collision
- bass/percussion masking
- energy trajectory
- short-term loudness continuity
- tempo-stretch artifacts
- pitch-shift artifacts
- clicks/pops/discontinuities
- transition-style appropriateness
- confidence/fallback behavior

A good engine must be able to decide that a complex DJ blend is the wrong transition for a given pair. This benchmark scores that decision explicitly (Lane E, §4.5) rather than assuming "more DSP processing is always better." **Symmetrically (R2), the benchmark must not punish an engine for correctly deciding a complex DJ blend *is* the right transition for a pair that only looks adversarial on paper** — see §6 (Condition Registry) and the `transition_class_policy` structure in the manifest schema.

### 3.1 Terminology gate (binding, per `.agents/skills/automix-forensic-research/SKILL.md`)

| Term | Meaning | Not satisfied by |
|---|---|---|
| Tempo/BPM-aware | scalar or estimated tempo used | — |
| Beat-aware | explicit beat timestamps/grid used | a derived `60000/BPM` theoretical grid (SimpMusic's actual mechanism, §8 level 2 of P0-M1) |
| Downbeat-aware | bar starts/downbeats identified and used | beat-awareness alone |
| Phrase-aware | transition entry/exit uses phrase boundaries | downbeat-awareness alone, or a fixed "every 32 beats" proxy (P0-M0 §7.2 documents this exact failure mode in `AI-DJ-Mixing-System`) |
| Section-aware | intro/verse/chorus/outro or equivalent structural sections identified and used | phrase-awareness alone |

Every benchmark report produced under this contract must classify the system under test against this table explicitly, using the same eight-level scheme P0-M1 §8 used for SimpMusic (`TEMPO_AWARE` → `CONFIDENCE_AWARE`), so results are comparable across systems and across time.

## 4. Benchmark lanes

Each lane is scored independently; a single aggregate score is explicitly disallowed (an engine that is excellent at Lane C and catastrophic at Lane A must not have that catastrophe averaged away). Every case type below must have at least one corresponding fixture/pair in the manifest (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §4 pair object, field `benchmark_lane` + `case_tags`); concrete representative pairs are enumerated in `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`, now with outcome-aware `transition_class_policy` per pair rather than a single fixed acceptable-class set (R2 — see §6).

### 4.1 Lane A — Timing / structure

| Case | Why it is adversarial to BPM/key-only systems |
|---|---|
| Same BPM, deliberately wrong beat phase | BPM match says "compatible"; SimpMusic-class engines have no way to detect or correct beat-1 offset (P0-M1 §10) |
| Beat-aligned but wrong downbeat/bar phase | Beats line up, but bar-1 of A lands on beat-3 of B |
| Same BPM/key, incompatible phrase timing | Both scalar signals say "go"; phrase structure says "don't" |
| Intro/outro opportunities present | Positive control — a system should use them when available |
| Chorus/drop/build-up boundary proximity | Tests section-aware entry/exit, not just phrase |
| Pickup/anacrusis starts | Track's first audible note precedes beat 1; naive "start at beat 1" logic mis-times |
| Long silence / non-musical tail | Tail has no beat content to align to; tests fallback, not beat-tracking |
| No clean intro/outro | Forces the planner to pick a non-boundary point deliberately, or fall back |
| Variable tempo (where feasible) | Defeats a single scalar-BPM model entirely |
| Non-4/4 or ambiguous meter (where feasible) | Defeats a hardcoded 4-beats-per-bar assumption (the exact assumption P0-M0 §7.2 found in `AI-DJ-Mixing-System`'s `beats[::4]` downbeat proxy) |

Note (R2): "adversarial" here describes the *input*, not the required *output*. A system that measurably corrects the beat phase/bar phase/phrase mismatch before executing a full blend is scored as having succeeded, not as having chosen the wrong class — see §6.

### 4.2 Lane B — Content collision

vocal→vocal · sustained vocal outro→vocal intro · dense bass→dense bass · percussion-heavy overlap · instrumental→vocal · sparse→dense · dense→sparse.

Rationale: P0-M1 §8 level 6 and §10 confirm SimpMusic has zero vocal/bass/percussion activity signal; its only "content-aware" behavior is a generic DJ-filter EQ sweep applied identically regardless of whether a real collision exists. This lane must contain pairs where a generic EQ sweep is *not* enough to avoid an audible collision, to distinguish "has an EQ effect" from "detects and avoids collisions." Where a fixture's collision is structurally unavoidable regardless of cue-point choice (continuous overlapping content through the whole candidate transition region, by construction), `FULL_DJ_BLEND` remains categorically `rejected` for that pair, not merely excluded by omission — see the pair catalog's explicit `reason` field for each such case.

### 4.3 Lane C — Energy / loudness

high→high · low→high · high→low · gradual buildup/drop · large mastering-loudness differences · locally quiet transition region despite high integrated loudness.

Rationale: P0-M1 §9/§10 confirms SimpMusic has exactly one loudness datum per track (a static integrated-loudness gain, applied outside the crossfade planner, not a time-varying contour). The "locally quiet transition region despite high integrated loudness" case specifically defeats any system using only integrated/track-level loudness, since it requires the *transition-window* loudness, not the whole-track average. **Loudness terminology in this lane and throughout this contract is binding (R1):** `momentary` = 400 ms integration window; `short-term` = 3 s integration window; `integrated` = programme/start-stop-style gated measurement. All three follow ITU-R BS.1770-5 for the underlying K-weighted measurement and true-peak algorithm; the `momentary`/`short-term`/`integrated` window-naming convention itself follows EBU R128 / EBU Tech 3341 practice, which BS.1770-5 does not itself name. These two terms are never used interchangeably or for the wrong window size anywhere in this contract or the manifest schema.

### 4.4 Lane D — Harmonic / tempo

compatible key + close tempo · compatible key + large tempo gap · incompatible key + close tempo · half/double-time cases · pitch shifting helps · pitch shifting should be avoided · stretch within reasonable range · stretch outside reasonable range.

Rationale: this lane is where a naive system is *most* likely to look competent (Camelot-wheel key scoring and half/double-time BPM normalization are both things SimpMusic already does correctly per P0-M1 §6, §11). The adversarial value here is in the boundary cases — tempo gaps and key incompatibilities specifically *outside* the range any bounded correction can fix (P0-M1 §10: SimpMusic's own ±25% BPM-ratio and ±2-semitone pitch bounds are evidence the authors know unbounded correction is unsafe, but tracks outside those bounds get *zero* correction, not a smarter decision) — this benchmark must confirm whether a system under test recognizes "this pair is outside safe correction range" and falls back, versus forcing a broken correction or ignoring the mismatch entirely. Per-pair `manipulation_constraints` (manifest schema §4) define exactly what "safe correction range" means for each pair, rather than leaving it as an undefined notion (R4).

### 4.5 Lane E — Confidence / fallback

Corpus must contain pairs where the expected preferred behavior is one or more of:

- `FULL_DJ_BLEND`
- `SHORT_EQ_BLEND`
- `SIMPLE_CROSSFADE`
- `GAPLESS`
- `CUT`
- `NO_SPECIAL_TRANSITION`

This lane scores whether the **chosen transition class** was appropriate, not only whether DSP execution was smooth — a technically flawless DJ blend applied to a pair that should have been a clean cut (e.g., sequential tracks from the same album/continuous mix, per P0-M0 §13's "sequential album tracks where transition may intentionally be suppressed" case) is a failure under this lane even if every other metric is clean. P0-M1 §8 level 8 and §13 confirm SimpMusic has no per-pair transition-style fallback at all (`djCrossfadeEnabled`/`crossfadeEnabled` are static global user settings) — this is the single gap this lane is designed to expose. Lane E carries a dedicated internal subset — pairs whose signals look compatible on paper but whose `transition_class_policy.rejected` categorically excludes `FULL_DJ_BLEND` for a real, annotation-grounded reason (e.g. a scripted content collision, per §4.2's note) — this subset is what the `C11`/G4 zero-tolerance check (§9, §11) is actually computed against, per R7.

## 5. Required baselines and comparability

### 5.1 Comparability classes

| Class | Meaning |
|---|---|
| `IDENTICAL_AUDIO_COMPARISON` | Same audio bytes/master run through both systems |
| `SAME_MASTER_LIKELY` | High confidence of the same master (same catalog release, same provider-reported duration/ISRC) but bytes not independently verified identical |
| `CATALOG_EQUIVALENT` | Same catalog track (title/artist/ISRC where available) but different provider/encode/master is plausible or confirmed |
| `NON_IDENTICAL_SOURCE_LIMITATION` | Comparison is on a materially different source (different remix/edit/live version, or provider forced substitution) |
| `SUBJECTIVE_REFERENCE_ONLY` | System cannot be run on our fixtures at all (closed catalog, no local-file import); scored as an observational quality reference only |

**Binding rule for statistical gates (R6):** a comparability class weaker than `IDENTICAL_AUDIO_COMPARISON` (i.e. `SAME_MASTER_LIKELY` or below) may never supply the quantitative n-count for any P1-gate statistical test in §11. `SAME_MASTER_LIKELY`/`CATALOG_EQUIVALENT` sessions may still be recorded and reported as qualitative/corroborating evidence, clearly labeled with their weaker comparability class, but they do not count toward a gate's required sample size.

### 5.2 Baseline systems

| # | System | Tier-1 (synthetic/local fixtures) | Tier-2 (commercial listening set) | Comparability | Notes / verification required |
|---|---|---|---|---|---|
| 1 | Fixed-duration equal-power crossfade | Our own reference implementation on Tier-1 audio | N/A | `IDENTICAL_AUDIO_COMPARISON` | Deterministic reference; this is the required, always-available quantitative baseline for `G1` (§11) |
| 2 | Clean cut / gapless | Our own reference implementation on Tier-1 audio | N/A | `IDENTICAL_AUDIO_COMPARISON` | Deterministic reference |
| 3 | Pinned SimpMusic AutoMix (actual) | If local-file playback is confirmed possible, run Tier-1 fixtures directly | Yes, via YouTube-resolved / Tidal-metadata-matched playback | Tier-1: `IDENTICAL_AUDIO_COMPARISON` if local import confirmed, else not runnable on Tier-1 at all. Tier-2: `CATALOG_EQUIVALENT` (Tidal-matched metadata against a YouTube-resolved stream is not guaranteed to be the same master, per P0-M1 §10's metadata-confidence-risk finding) | Score Auto-duration mode with DJ mode **on** and **off** separately, per P0-M1 §15. See R6 fallback path below (item 3a). |
| 3a | `SIMPMUSIC_CLASS_REFERENCE` (clean-room, R6) | Our own Tier-1-runnable implementation | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | **New (R6).** A clean-room re-implementation of SimpMusic's published/pinned AutoMix *algorithm* as documented with exact constants in `docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §6 (equal-power crossfade curve, `resolveAutoCrossfadeDurationMs` formula, BPM/key gap factors, Camelot distance, bounded tempo/pitch-ratio functions) — every one of these is already classified `REIMPLEMENT_CLEAN_ROOM` in P0-M1 §12, so this reference implements the *published formulas*, never SimpMusic/`core`'s GPLv3 Kotlin source. This is the guaranteed-available Tier-1 quantitative stand-in for `G2` (§11) whenever actual SimpMusic cannot consume Tier-1 fixtures — see the "SimpMusic baseline path" decision rule below. |
| 4 | Echo Music AutoMix beta | `UNKNOWN_NEEDS_RUNTIME_PROOF` whether local files can be loaded | Not established | Default `NON_IDENTICAL_SOURCE_LIMITATION` until local-file capability is confirmed | P0-M0 §7.1 traced its beat-analysis code but not its file-source capability; not load-bearing for any G-gate |
| 5 | Apple Music AutoMix | Cannot run Tier-1 (closed catalog, no local import) | Yes | `SUBJECTIVE_REFERENCE_ONLY` for structure; `CATALOG_EQUIVALENT` at best for Tier-2 (Apple's own masters) | Observable behavior only; never infer internals (P0-M0 §2); not load-bearing for any G-gate |
| 6 | Spotify playlist mixing `Auto` | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Same constraint; not load-bearing |
| 7 | Algoriddim djay Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` — djay documents local-library support; not verified in this task | Yes, via Spotify/Apple Music integration | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON` pending verification; Tier-2 `CATALOG_EQUIVALENT` | djay is the primary licensed-integration benchmark per P0-M0 §4; not load-bearing for any G-gate |
| 8 | Offtrack | Cannot run Tier-1 (provider-only per P0-M0 §3, no confirmed local import) | Yes, via Spotify/Apple Music/SoundCloud | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Primary consumer benchmark per P0-M0 §3; not load-bearing |
| 9 | rekordbox Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` — rekordbox is local-library-centric by design, so Tier-1 is plausible | Yes, via Spotify Automix (7.2.16+) | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON` pending verification; Tier-2 `CATALOG_EQUIVALENT` | Professional reference, benchmark "where practical" per Issue #4; not load-bearing |
| 10 | Future AutoMix engine revisions | Full Tier-1 corpus, every version | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | This is the internal regression-testing baseline; every future engine change is scored against the same pinned fixture set |

No proprietary internals are invented for #4–#9 anywhere in this contract or its companions; only publicly observable behavior, first-party documentation (already cited in P0-M0 §2), and — where marked `UNKNOWN_NEEDS_RUNTIME_PROOF` — behavior that must be hands-on verified before that system can be scored, not assumed.

### 5.3 SimpMusic baseline path (R6 — cannot become impossible by construction)

`G2` (§11) requires a quantitative, statistically powered comparison against SimpMusic-class AutoMix behavior. Because whether *actual* SimpMusic can consume Tier-1 local fixture files is unverified (`UNKNOWN_NEEDS_RUNTIME_PROOF`, §5.2 row 3), the gate is defined so it is satisfiable either way:

1. **If actual SimpMusic is confirmed (via a future hands-on runtime check) to accept local Tier-1 fixture files for playback**, `G2`'s quantitative n≥`g2_simpmusic_comparison_subset_min` gate (§11, §manifest `corpus_minimums`) is satisfied using **actual SimpMusic** directly, run on the same Tier-1 audio bytes, comparability = `IDENTICAL_AUDIO_COMPARISON`. `SIMPMUSIC_CLASS_REFERENCE` (§5.2 row 3a) becomes an optional secondary corroborating baseline, not load-bearing.
2. **If actual SimpMusic is confirmed not to support local-file playback, or this remains unverified by the time `G2` needs to be evaluated**, `G2`'s quantitative gate is satisfied using **`SIMPMUSIC_CLASS_REFERENCE`** instead — comparability `IDENTICAL_AUDIO_COMPARISON` by construction, since it is our own Tier-1-runnable clean-room implementation of the published SimpMusic algorithm. Actual SimpMusic is then retained purely as a Tier-2 observational/subjective reference (`CATALOG_EQUIVALENT`, scored qualitatively per §8), and **never** supplies the quantitative n-count for `G2` (per the §5.1 binding rule).
3. Either path keeps `G2` executable without waiting on an unresolved runtime question, and without ever silently waiving the SimpMusic comparison entirely, satisfying the R6 instruction directly. A benchmark report executing this contract must state explicitly which of the two paths it used and why.
4. `SIMPMUSIC_CLASS_REFERENCE`'s clean-room boundary is preserved identically to P0-M1 §12's disposition table: it is built from the published formulas and public DSP identities already cited there (equal-power crossfade, Audio EQ Cookbook biquad design, Camelot wheel, half/double-time normalization, bounded ratio search), never from SimpMusic/`core`'s GPLv3 source, and it must not be described in any report as "SimpMusic" without the `_CLASS_REFERENCE` qualifier, to avoid misattributing its results to the actual shipping product.

## 6. Condition Registry (new — R2, R4)

Named, reusable objective conditions that a pair's `transition_class_policy.accepted_conditional` entries (manifest schema §5) reference by ID. This registry exists so that "the engine corrected the adversarial input well enough to justify a full blend" is a precise, falsifiable, metric-referencing statement rather than a judgment call — and so that catastrophic-failure thresholds `C5`/`C7`/`C8` (§9) reference the same named constants instead of an undefined "safe envelope" or "high-co-activity threshold" (R4).

| Condition ID | Definition | References |
|---|---|---|
| `COND_BEAT_OK` | Beat-alignment error (beat-fraction) ≤ 1/16 (6.25%) at the chosen anchor point | Beat alignment error metric (§7) |
| `COND_DOWNBEAT_OK` | Downbeat/bar-phase error = 0 beat positions | Downbeat/bar-phase error metric (§7) |
| `COND_CUE_OK` | Cue-region error = 0 ms (chosen entry/exit point lands inside an annotated acceptable region) | Cue-region error metric (§7) |
| `COND_PHRASE_OK` | Phrase-boundary distance ≤ 0.5 × the local beat period | Phrase-boundary distance metric (§7) |
| `COND_SECTION_OK` | Section-boundary distance ≤ 1 × the local bar period (4 × beat period for 4/4; meter-scaled otherwise) | Section-boundary distance metric (§7) |
| `COND_TEMPO_ENVELOPE_OK` | Applied tempo-ratio deviation from 1.0 ≤ the pair's `manipulation_constraints.tempo_ratio_max_deviation` (default **0.12**, i.e. 12%) | Applied tempo ratio metric (§7); default derivation below |
| `COND_PITCH_ENVELOPE_OK` | Pitch-shift magnitude ≤ the pair's `manipulation_constraints.max_pitch_shift_semitones` (default **3 semitones**) | Pitch shift metric (§7) |
| `COND_VOCAL_OK` | Vocal-overlap ratio ≤ 0.3 **and** vocal-overlap duration ≤ 2000 ms | Vocal overlap metric (§7) — deliberately tighter than the `C4` catastrophic bar (60%/4 s), i.e. this is a "good outcome" bar, not merely "not catastrophic" |
| `COND_BASS_OK` | Bass-overlap proxy (§ `C5` co-activity definition below) covers ≤ the pair's `manipulation_constraints.low_band_coactivity_ratio_ceiling` (default **0.5**, i.e. 50%) of the transition window | Bass-overlap proxy metric (§7); `C5` definition (§9) |
| `COND_LOUDNESS_OK` | Momentary loudness delta ≤ 2 LU | Momentary loudness delta metric (§7) |

**Default derivation for `tempo_ratio_max_deviation` (12%):** P0-M1 §6 documents SimpMusic's own shipped ceiling as `BPM_RATIO_MIN/MAX` = ±25% — the original engineers' own evidence that stretch beyond that range is considered unsafe. AutoMix's target quality bar is intentionally tighter than merely matching that ceiling, not just replicating it; 12% (roughly half of SimpMusic's bound) is set as a defensible initial default pending empirical DSP-artifact-threshold testing with Signalsmith Stretch (`docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) once a prototype exists — a future task, not this specification, is expected to tighten or loosen this number with real measurement evidence.

**Default derivation for `low_band_coactivity_threshold_db`/`ratio_ceiling` (−12 dB / 500 ms / 50%):** "high co-activity" (used by `C5`, §9) is defined as: both tracks' low-band (20–150 Hz) short-term RMS energy simultaneously at or above −12 dB relative to that track's own low-band peak RMS (measured over the fixture's full duration), sustained for ≥ 500 ms continuously. −12 dB relative to peak corresponds to roughly 25% of peak amplitude — a standard "clearly active, not merely a decay tail" cutoff consistent with common onset/activity-detection heuristics; the 500 ms minimum duration excludes brief incidental overlaps (e.g. two transient hits that happen to land close together) from counting as sustained masking. `C5` then fires when this co-activity condition holds for > 50% of a transition window shorter than 4000 ms.

Every default above is a manifest-schema field with an explicit fallback value (manifest schema §4 `manipulation_constraints`), never a bare prose number with no corresponding field — this is the direct fix for R4's "a catastrophic gate may not depend on an undefined variable."

## 7. Objective metrics

Every metric below is tagged `OBJECTIVE`, `PROXY`, or `HUMAN_ONLY` per `.agents/skills/automix-task-contract/SKILL.md`'s evidence-gate discipline: `OBJECTIVE` metrics are computed deterministically from ground-truth annotations or the transition-window waveform with no subjective judgment; `PROXY` metrics stand in for a perceptual quality that cannot be measured directly and must be validated against the human rubric (§8) before being trusted alone; `HUMAN_ONLY` has no defensible automated substitute.

| Metric | Formula / method | Unit | Required ground truth | Interpretation | Threshold/range | Limitation | Class |
|---|---|---|---|---|---|---|---|
| Beat alignment error | `min(\|t_actual − t_nearest_grid_beat\|, beat_period − \|...\|)` at the chosen transition anchor point | ms and beat-fraction (`error_ms / beat_period_ms`) | Beat timestamps (`SYNTHETIC_EXACT` preferred) for both tracks | Lower is better; 0 = perfectly on-beat | `COND_BEAT_OK`: ≤ 1/16 beat (6.25%) | Meaningless for tracks with no reliable beat grid (weak-beat/rubato material) — mark `N/A`, do not impute 0 | `OBJECTIVE` (when ground truth is `SYNTHETIC_EXACT`/`MANUAL`); `PROXY` when ground truth is `MODEL_ESTIMATE` |
| Downbeat/bar-phase error | Circular distance, in beat positions, between the incoming track's landing beat and the nearest downbeat of the bar grid it entered | integer beat positions (0 = correct bar) | Downbeat/bar-start annotations | 0 = correct bar phase | `COND_DOWNBEAT_OK`: = 0 | Requires a defined meter; `N/A` for ambiguous-meter fixtures (recorded explicitly, per Lane A) | `OBJECTIVE` |
| Cue-region error | Distance from chosen entry/exit point to the nearest edge of the nearest annotated acceptable region; 0 if inside a region | ms | Acceptable entry/exit region annotations | 0 = inside an annotated-good region | `COND_CUE_OK`: = 0 | Acceptable regions are themselves `MANUAL` or `MODEL_ESTIMATE` in non-synthetic material — record source | `OBJECTIVE` for `SYNTHETIC_EXACT`/`MANUAL` regions; `PROXY` otherwise |
| Phrase-boundary distance | `min(\|t − nearest_phrase_boundary\|)` | ms | Phrase-boundary annotations | Lower is better | `COND_PHRASE_OK`: ≤ 0.5 × beat period | Phrase boundaries in non-synthetic material are frequently `MODEL_ESTIMATE`; do not treat as exact | `OBJECTIVE` (`SYNTHETIC_EXACT`/`MANUAL`); `PROXY` (`MODEL_ESTIMATE`) |
| Section-boundary distance | Same method as phrase-boundary, against section annotations | ms | Section boundary/label annotations | Lower is better where a section-aware entry/exit was expected | `COND_SECTION_OK`: ≤ 1 × bar period | Section labels are coarser and less reliable than phrase boundaries even for `MANUAL` annotation — always record annotator confidence | `PROXY` |
| Vocal overlap duration/ratio | Sum of ms where both tracks' vocal-activity intervals are simultaneously active within the transition window; ratio = overlap / transition-window duration | ms and ratio [0,1] | Vocal activity intervals | Lower is better for non-intentional collisions | `COND_VOCAL_OK`: ratio ≤ 0.3 and duration ≤ 2000 ms; see `C4` (§9) for the catastrophic threshold | Vocal-activity ground truth for real material is usually `MODEL_ESTIMATE` (a vocal-activity detector) unless `MANUAL`-annotated; never `SYNTHETIC_EXACT` except for synthetic fixtures with a scripted "vocal-band" stem | `OBJECTIVE` (synthetic); `PROXY` (real material) |
| Bass-overlap proxy | Co-occurrence of both tracks' low-band (20–150 Hz) short-term RMS energy each ≥ `low_band_coactivity_threshold_db` relative to that track's own low-band peak, sustained ≥ `low_band_coactivity_min_duration_ms`, integrated as a ratio of the transition window | ms and ratio [0,1] | Bass/percussion activity intervals, or raw low-band energy if intervals are unavailable | Lower is better | `COND_BASS_OK`: ratio ≤ `low_band_coactivity_ratio_ceiling` (default 0.5); see `C5` (§9) | This is explicitly a **proxy** — RMS co-occurrence is not the same as perceptual masking, which also depends on spectral overlap, not just band energy; do not present this as a measured masking amount | `PROXY` |
| Momentary loudness delta | `\|LUFS_momentary(t_post) − LUFS_momentary(t_pre)\|`, each measured with a **400 ms** integration window (ITU-R BS.1770-5 K-weighting, EBU Tech 3341 momentary-metering convention), sampled immediately before and after the transition's committed point | LU | None beyond the audio itself | Lower is better | `COND_LOUDNESS_OK`: ≤ 2 LU; see `C6` (§9) for the catastrophic threshold | Momentary windows are short enough to be sensitive to genuinely intentional short-duration dynamics; always inspect alongside the waveform, not as a lone pass/fail | `OBJECTIVE` |
| Short-term loudness continuity | Trend comparison of **3 s**-window loudness (ITU-R BS.1770-5 short-term convention) sampled across the transition region, before vs. after | LU (trend delta) | None beyond the audio | Smaller discontinuity is better | No universal target; scored per Lane C case type | Coarser and less sensitive to instantaneous jumps than the momentary metric by design — this is the broader-trend companion, not a duplicate | `OBJECTIVE` |
| Transition-window loudness discontinuity | Maximum instantaneous derivative of the momentary loudness curve (400 ms window, 100 ms hop) across the transition window, compared against the same track's typical (non-transition) momentary-loudness derivative baseline | LU/s (momentary-basis) | None beyond the audio | Lower relative-to-baseline is better | See `C6` (§9) | Sensitive to fixture length/dynamics; always report relative to the track's own baseline, not an absolute cross-track number. **This metric and "momentary loudness delta" above are both momentary-basis, not short-term-basis — never label either one "short-term" (R1).** | `OBJECTIVE` |
| Energy-continuity delta/slope | Difference between the pre-transition RMS-energy trend slope and the post-transition RMS-energy trend slope, fit over a fixed window (default 4 s each side, configurable per fixture) | dB/s difference | None beyond the audio | Smaller discontinuity in slope is better | No universal target; scored per Lane C case type (e.g., "gradual buildup/drop" expects a *specific* nonzero slope match, not zero) | RMS-energy slope is a coarse proxy for perceived "momentum"; does not capture spectral energy shifts | `PROXY` |
| Applied tempo ratio / max deviation | Ratio of executed playback rate to the track's native tempo at each point in the transition; report both the target ratio and observed max instantaneous deviation from it | ratio (dimensionless), max deviation in % | None beyond engine-reported/measured playback rate | Closer to 1.0 (or to the intentionally chosen ratio) is generally safer | `COND_TEMPO_ENVELOPE_OK`: deviation ≤ `tempo_ratio_max_deviation` (default 12%); see `C7` (§9) | Ratio alone does not capture stretch-algorithm artifact quality — always pair with the human DSP-smoothness rating (§8) | `OBJECTIVE` |
| Pitch shift in semitones | `12 · log2(f_shifted / f_original)` | semitones | None beyond engine-reported/measured pitch shift | Smaller magnitude is generally safer | `COND_PITCH_ENVELOPE_OK`: magnitude ≤ `max_pitch_shift_semitones` (default 3); see `C8` (§9) | Same caveat as tempo ratio — pair with human rating | `OBJECTIVE` |
| Click/pop/discontinuity/dropout candidate flag | Detector flags sample-domain waveform discontinuities (magnitude of second difference exceeding a defined multiple of the local noise floor) at/near the splice or commit boundary, and flags any silence/zero-buffer run inconsistent with the source material | count + timestamps | None beyond the audio | 0 candidate flags is the target | See `C9` (§9) — **a raw flag is a candidate, not a confirmed defect (R3)** | A heuristic detector; false positives on genuinely percussive/transient material are expected — a candidate flag must be corroborated (deterministically or by blinded human listening, §9) before counting toward any gate | `PROXY` |
| Clipping / true-peak | True-peak level per ITU-R BS.1770-5 oversampled true-peak measurement across the transition window | dBTP | None beyond the audio | Target ≤ −1 dBTP | Flag any sample ≥ −1 dBTP | Only relevant where the engine applies gain (loudness compensation, DJ-filter gain); not relevant to pure pass-through segments | `OBJECTIVE` |
| Transition duration | Wall-clock duration of the executed transition window, as actually scheduled by the system under test | ms | None beyond engine-reported/measured timing | Reported, not judged in isolation | Compared against the fixture's `transition_class_policy` | A short duration is not inherently a defect (e.g., `SIMPLE_CROSSFADE`/`CUT` are expected to be short) — always interpret alongside transition-class correctness | `OBJECTIVE` |
| Transition-class correctness | Categorical evaluation of the system's chosen class against the pair's `transition_class_policy` (manifest schema §5): `accepted_unconditional` → correct; `accepted_conditional` → correct **iff** the stated condition IDs are measured-satisfied by this execution, else mismatch; anything else (including any listed `rejected` class) → mismatch, and a `rejected`-class mismatch is additionally the annotation-grounding trigger for `C11` (§9). Reported per-pair and as a full confusion matrix across the corpus. | categorical (correct / mismatch) + confusion matrix | `transition_class_policy` annotation (manifest schema §5) | Correct is better | See §11 (`G4`) for the required match-rate threshold | This metric is now **outcome-aware (R2)**: choosing `FULL_DJ_BLEND` on an adversarial-looking pair is scored correct when the engine actually satisfies the pair's stated conditions, not automatically wrong because the input was adversarial | `PROXY` (the policy itself is `MANUAL`/`SYNTHETIC_EXACT`-authored intent, not a measured ground truth of "the one correct answer") |

## 8. Human listening rubric

Human listening is **mandatory** and has **veto authority** over any automated PASS. No pair may be marked as passing on the strength of objective/proxy metrics alone if a human listener flags it as broken.

### 8.1 Scale

Anchored 1–5 scale (not an unexplained 1–10, per Issue #4), used for rubric dimensions 1–15:

| Score | Meaning |
|---|---|
| 1 | Clearly broken |
| 2 | Poor / clearly undesirable |
| 3 | Acceptable / not distracting |
| 4 | Good / intentional |
| 5 | Excellent / difficult to improve materially |

`N/A` is always a valid response (e.g., "vocal handling" on an instrumental-only pair).

### 8.2 Scored dimensions (per pair)

1. Entry-point naturalness
2. Exit-point naturalness
3. Beat coherence
4. Downbeat/bar coherence
5. Phrase coherence
6. Section coherence
7. Vocal handling
8. Bass/frequency handling
9. Energy flow
10. Loudness continuity
11. Tempo/stretch naturalness
12. Pitch/key naturalness
13. DSP smoothness
14. Transition-style appropriateness
15. Overall musical intentionality

**Dimension 16 — Preference vs. baseline (R5, redefined as a categorical outcome, not a 1–5 score):** every pair is played to the listener in both its candidate-system rendering and its fixed equal-power-crossfade baseline rendering (§5.2 #1), blinded and order-randomized. The listener records exactly one of:

- `CANDIDATE_PREFERRED`
- `BASELINE_PREFERRED`
- `TIE`

An optional free-text magnitude note may accompany the outcome (e.g., "clear win" vs. "marginal") but is not used in the statistical computation in §11 — only the three-way categorical outcome is. This is the exact data model `G1`'s binomial test (§11) consumes.

Plus one free-text field for a **veto flag**, independent of both the 1–5 scores and dimension 16: `CATASTROPHIC_FAILURE_OBSERVED: yes/no + code (§9) + free-text note`. Any veto invocation forces the pair to `FAIL` regardless of every other score (§9).

### 8.3 Procedure

- **Blinded/randomized**: listeners are not told which system (baseline, SimpMusic, `SIMPMUSIC_CLASS_REFERENCE`, AutoMix candidate, etc.) produced a given transition; playback order and system identity are randomized per session and logged separately from the listener-facing session.
- **Single-owner procedure (initial)**: the project owner conducts blinded sessions using a randomized playback queue generated from the manifest; system identity is revealed only after all scores for a session are recorded, never during.
- **Multi-rater procedure (later)**: additional listeners score the same blinded queues independently; report inter-rater agreement (e.g., Krippendorff's alpha or simple pairwise agreement rate) per dimension once ≥ 2 raters exist. Do not average away persistent disagreement — report the distribution, not just the mean, when raters diverge by ≥ 2 points on any 1–5 dimension, or disagree on the dimension-16 categorical outcome.
- Every human-rated pair must record: rater ID (or "owner" for the single-rater phase), session timestamp, playback order position, and whether the rater was blinded successfully (self-reported — did they guess the system?).

## 9. Catastrophic failures

Any **confirmed** code below triggers an automatic pair-level `FAIL`, independent of aggregate metric averages, and counts toward the catastrophic-failure-rate gate in §11 (`G6`). A human listener's veto flag (§8.2) can also independently trigger `FAIL` even if no automated detector fired, logged as `HUMAN_VETO` and gated separately as `G7`. Conversely, an automated code firing is never silently downgraded — a human reviewer may annotate a firing as a false positive, but that annotation and its justification are recorded in the result log, not used to delete the event.

| Code | Definition | Threshold / detection (all constants defined — R4) | Gate consequence |
|---|---|---|---|
| `C1_BEAT_TRAINWRECK` | Sustained audible beat drift on a pair the system declared beat-synced | Beat-alignment error > 1/8 beat (12.5%) for > 50% of the overlap window, on pairs with `SYNTHETIC_EXACT`/`MANUAL` beat ground truth and BPM gap ≤ 3% | Pair `FAIL`; safety-critical (`G6` zero-tolerance on holdout) |
| `C2_BAR_PHASE_ERROR` | Wrong beat-in-bar landing on a bar-synced pair | Downbeat/bar-phase error > 0 beat positions when the system declared bar-synced execution and meter/downbeat ground truth exists | Pair `FAIL`; safety-critical |
| `C3_WRONG_PHRASE_LOCATION` | Entry/exit lands outside any acceptable region and more than one full phrase (or 8 bars, where phrase is unknown) from the nearest boundary | Cue-region error exceeds the phrase/8-bar distance, for pairs where the system's chosen class was `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` (regardless of whether that class choice itself was `accepted_unconditional`/`accepted_conditional`/`rejected` — this code is about execution quality of a blend-style class, not about the class-choice question, which is `C11`'s and `G4`'s domain) | Pair `FAIL` |
| `C4_SEVERE_VOCAL_COLLISION` | Two independently active (non-intentional) vocal lines overlap heavily | Vocal-overlap ratio > 60% **and** overlap duration > 4 s | Pair `FAIL`; safety-critical |
| `C5_SEVERE_BASS_MASKING` | Full-energy bass-on-bass collision in a short transition | Bass-overlap proxy (§6 co-activity definition: both tracks' low-band RMS ≥ `low_band_coactivity_threshold_db` [default −12 dB relative to each track's own peak], sustained ≥ `low_band_coactivity_min_duration_ms` [default 500 ms]) covers > 50% of a transition window shorter than 4000 ms | Pair `FAIL` |
| `C6_GROSS_LOUDNESS_DISCONTINUITY` | Audible loudness jump at or during the transition, measured on the **momentary** (400 ms) basis (R1 — never the 3 s short-term basis) | Instantaneous momentary-loudness jump > 6 LU between consecutive 100 ms-stepped momentary measurements, or > 3 LU momentary step at a `CUT`/`GAPLESS` splice boundary | Pair `FAIL`; safety-critical |
| `C7_STRETCH_ARTIFACT` | Tempo correction pushed far enough to produce an audible artifact | Applied tempo-ratio deviation exceeds the pair's `manipulation_constraints.tempo_ratio_max_deviation` (default 12%, §6) **and** human DSP-smoothness rating (dimension 13) ≤ 2 | Pair `FAIL` |
| `C8_PITCH_ARTIFACT` | Pitch correction produces an audible artifact | Pitch shift magnitude exceeds the pair's `manipulation_constraints.max_pitch_shift_semitones` (default 3, §6), or any shift paired with human pitch/key-naturalness rating (dimension 12) ≤ 2 | Pair `FAIL` |
| `C9_CLICK_POP_DROPOUT` | Audible discontinuity or dropout at/near the splice/commit boundary | **Two-stage (R3, fixes the PROXY-vs-safety-critical contradiction):** (1) `C9_CANDIDATE` — the click/pop/discontinuity detector fires above threshold, OR a silence/zero-buffer run inconsistent with source material is detected. Logging this alone does **not** fail the pair and does **not** count toward `G6`. (2) `C9_CONFIRMED` — a `C9_CANDIDATE` event is corroborated by **either** (a) deterministic, source-grounded evidence of an actual digital dropout/underrun (e.g. a genuine zero-buffer/silence run with no corresponding silence in either source fixture — this sub-case is itself `OBJECTIVE`, not proxy, since a real underrun is unambiguous), **or** (b) a blinded human listener independently rating the same transition's DSP smoothness (dimension 13) ≤ 2 **or** invoking the veto flag, with a timestamp within ±250 ms of the candidate flag. Only `C9_CONFIRMED` triggers pair `FAIL` and counts toward `G6`'s zero-tolerance holdout gate; `C9_CANDIDATE`-only events are retained in the run log as diagnostic signal for future detector tuning, never presented as a confirmed defect. | Pair `FAIL` **only when `C9_CONFIRMED`**; safety-critical in its confirmed form only |
| `C10_WRONG_METADATA_POISONING` | Engine's BPM/key input diverges from fixture ground truth and measurably drives a bad decision | Input BPM off by > 3 (non-half/double-time-equivalent) or input key off by > 1 Camelot step from `SYNTHETIC_EXACT`/`MANUAL` ground truth, **and** this is traceable to the resulting timing/class decision | Pair `FAIL`; directly tests the exact failure mode P0-M1 §10 identifies as SimpMusic's single largest correctness risk (Tidal duration-matched metadata poisoning) |
| `C11_FORCED_WRONG_TRANSITION_STYLE` | Engine chose a transition class the pair's own annotation explicitly rejects, corroborated by evidence — **not** inferred from an undefined notion of "strong signals" (R7) | Fires **only** when: (a) the system's chosen class appears in the pair's `transition_class_policy.rejected` list (manifest schema §5 — an explicit, authored, reasoned annotation, never inferred at scoring time), **and** (b) at least one of: (i) a specific objective metric named in that `rejected` entry's context breached its stated threshold as a measured consequence of executing the rejected class, or (ii) a blinded human listener independently rated transition-style appropriateness (dimension 14) ≤ 2, or invoked the veto flag, for this pair | Pair `FAIL`; directly tests Lane E's dedicated adversarial subset (§4.5, §11 `G4`) |

"Safety-critical" codes (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`, plus any `HUMAN_VETO`) require a **zero** occurrence rate on the Tier-1 holdout split for the P1 gate (§11, `G6`/`G7`) — these are the failure modes that make a transition *unlistenable*, as distinct from merely suboptimal.

## 10. Anti-overfitting

The benchmark must not be EDM/4-on-the-floor-only — this is the same trap P0-M0 §7.2/§7.4 flags for both `AI-DJ-Mixing-System` (fixed-beat-count phrase/bar proxies) and CUE-DETR (EDM-heavy training domain that "may generalize poorly to pop/hip-hop/rock/non-4/4 material").

- Coverage plan: pop, hip-hop, R&B, rock, electronic, acoustic, ballad, dynamic-tempo/live material where legally obtainable, unusual intros/outros, and non-4/4 cases where musically appropriate.
- Every lane (§4) must have representation outside 4/4 EDM-style material once the corpus matures beyond its initial synthetic seed set; the pair catalog (`docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`) tracks genre/style tag distribution explicitly so this can be audited, not assumed.
- **Holdout pairs/categories may not be hand-tuned.** Any threshold, heuristic, or fixture adjustment made in response to a specific holdout pair's result invalidates that holdout pair — it must be either retired from holdout (and replaced) or the tuning must be reverted. This rule exists specifically so P1-gate numbers (§11) cannot be gamed by iterating against the holdout set.

## 11. P0 → P1 gate

P1 (local AutoMix engine **production** implementation) remains **BLOCKED** until a future provider-independent prototype demonstrates **all** of gates `G1`–`G8` below. **Clarification (R8):** this blocks the *production, shipping* engine only. P0-M3 (or any future task) building a disposable, non-shipping benchmark-execution prototype in order to actually measure these gates is not itself blocked by them — a prototype whose sole purpose is producing the evidence a gate requires cannot be circularly gated behind that same gate.

These are proposed initial numbers grounded in standard practice for paired-preference testing and in the specific gaps P0-M1 documents; they are explicitly not tuned against any existing implementation (none exists) and must not be loosened later merely to make a specific candidate pass — any change requires a PM-reviewed rationale recorded in a future document, not a silent edit here.

### Minimum corpus / gate sample-size plan (R5, R6 — makes G1–G5 mathematically executable)

All minimums below are also encoded machine-readably in `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §2 `manifest.json.corpus_minimums`, which is the single source of truth a benchmark runner reads; this prose must not drift from that block without a coordinated schema-version bump.

- **Tier-1 total corpus minimum: 60 pairs**, split `dev` 42 / `holdout` 18 (30% holdout, per the manifest's `holdout_fraction_target`).
- **Per-lane minimum**: Lane A ≥ 16, Lane B ≥ 8, Lane C ≥ 8, Lane D ≥ 12, Lane E ≥ 16 (sums to 60). Lane A and Lane E receive the largest allocation because they are, respectively, the lane P0-M1 §16 identifies as the highest-value floor to beat (beat/downbeat/cue/phrase) and the lane exposing SimpMusic's single largest architectural gap (no per-pair transition-style fallback, P0-M1 §8 level 8/§13).
- **Lane A "clean structure" subset** (used by `G3`, excludes deliberately-adversarial no-clean-intro/outro pairs by design): minimum 10 pairs, a subset of Lane A's 16.
- **Lane E "should-not-full-blend" adversarial subset** (used by `G4`'s `C11` zero-tolerance check, §4.5/§9): minimum 8 pairs, a subset of Lane E's 16.
- **`G2` SimpMusic-comparison subset**: a fixed 30-pair subset of the Tier-1 corpus, itself split 21 `dev` / 9 `holdout` (same ~30% ratio) — satisfies the required n≥30 with a defined holdout component.

### G1 — Materially better blind human preference than fixed-duration equal-power crossfade

Recorded per §8.2 dimension 16 as `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE` for every Tier-1 pair.

**Tie handling (R5, explicit, not silently coerced):** ties are excluded from the win-rate ratio's numerator/denominator (`win_rate = CANDIDATE_PREFERRED / (CANDIDATE_PREFERRED + BASELINE_PREFERRED)`, i.e. computed over *decisive* trials only) but are always reported alongside the win rate as their own statistic (`tie_rate = TIE / n_total`). If `tie_rate > 20%` across the trials being evaluated for a given gate check, that check is **inconclusive regardless of the decisive-trial win rate** — more trials under the same protocol must be collected before `G1` can be claimed satisfied; a high tie rate is not itself grounds to relax the win-rate requirement.

**Threshold:** one-sided exact binomial test against null `p₀ = 0.5` (`H₁: p > 0.5`), computed over decisive trials (`k = CANDIDATE_PREFERRED` count, `n = CANDIDATE_PREFERRED + BASELINE_PREFERRED`):

- Combined `dev`+`holdout`: `n ≥ 40` decisive trials (drawn from the 60-pair corpus, §above), observed win rate ≥ 65% (`k/n ≥ 0.65`), exact binomial `p < 0.05`.
- `holdout` alone: `n ≥ 18` decisive trials (all 18 holdout pairs, assuming a low tie rate; if tie rate on holdout exceeds 20% per the rule above, more holdout-protocol trials are needed), observed win rate ≥ 60%. **This holdout-alone check is a point-estimate corroboration, not an independently significance-tested claim** — at practical holdout sample sizes for a project at this scale, requiring `p < 0.05` on the holdout subset alone would demand an impractically large holdout corpus (see the worked example below). This limitation is stated explicitly rather than silently implying more statistical rigor than the sample size supports.

**Worked boundary example (R5 required validation item 4 — exact binomial, computed via `scipy`-equivalent exact summation, not a normal approximation):**

| n | k (wins) | Observed win rate | Exact one-sided p-value (`H₁: p>0.5`) | Passes `p<0.05`? |
|---|---|---|---|---|
| 40 | 26 | 65.0% | **0.0403** | Yes — this is the exact `G1` combined-split boundary case; 65%/40 clears the bar with margin to spare (p just under 0.05) |
| 40 | 25 | 62.5% | 0.0769 | No — confirms the 65% threshold is meaningfully binding, not trivially satisfied by any win rate above 50% |
| 18 | 11 | 61.1% | 0.2403 | No — at the holdout minimum n=18, even a 61% win rate is far from p<0.05, confirming the "point-estimate, not significance-tested" characterization above is honest, not a loophole |
| 18 | 10 | 55.6% | 0.4073 | No |

These four rows demonstrate the stated percentage/n/p-value semantics are internally consistent and non-contradictory: the 65%/n≥40 combined threshold is calibrated to just clear `p<0.05`, and the 60%/n≥18 holdout threshold is explicitly documented as not independently significance-tested at that sample size, rather than the two thresholds silently implying incompatible statistical claims.

### G2 — Materially better quality/preference than SimpMusic-class AutoMix

Using the baseline path defined in §5.3 (actual SimpMusic if local-fixture playback is confirmed, else `SIMPMUSIC_CLASS_REFERENCE`), run Auto-mode+DJ-mode-on (SimpMusic's most feature-complete configuration per P0-M1 §15): mean overall-preference (rubric dimension 15, the 1–5 anchored scale — **not** dimension 16's categorical outcome, since this comparison is not against the equal-power-crossfade baseline) ≥ SimpMusic-class score + 0.5, on the `G2` 30-pair subset (§above), `n ≥ 30` combined, holdout component `n ≥ 9` evaluated independently (no separate significance test required at n=9, same point-estimate caveat as `G1`'s holdout check).

### G3 — Real beat/downbeat/cue/phrase-aware behavior, not `60000/BPM` theoretical grids

On the Lane-A "clean structure" subset (§above, minimum 10 pairs): median beat-alignment error ≤ 1/16 beat (`COND_BEAT_OK`) and median downbeat/bar-phase error = 0 (`COND_DOWNBEAT_OK`) for pairs where the system declares beat/bar-synced execution; entry/exit point falls inside an annotated acceptable region (`COND_CUE_OK`) in ≥ 90% of those pairs — at n=10, 90% requires ≥ 9/10 successes exactly (no rounding ambiguity at this corpus size).

### G4 — Confidence-aware fallback that sometimes intentionally chooses a simpler transition

On all Lane E pairs (minimum 16, §above): transition-class match rate (§7 "Transition-class correctness," outcome-aware per R2) ≥ 80% overall. On the Lane E "should-not-full-blend" adversarial subset specifically (minimum 8, §above): `C11_FORCED_WRONG_TRANSITION_STYLE` confirmed-event rate = 0% (0 of ≥ 8).

### G5 — Success on unseen holdout pairs

Every threshold in `G1`–`G4` above must hold independently on each gate's own holdout component (already specified inline per gate above: 18 for `G1`, 9 for `G2`, the Lane-A clean-structure subset's own holdout portion for `G3`, the Lane-E adversarial subset's own holdout portion for `G4`) — not only on the `dev` split — with no pair-specific tuning permitted on holdout (§10). This item is deliberately not a separate numeric threshold; it is the requirement that every other gate's stated holdout figures are met, closing the "G5 references undefined holdout counts" gap from the original draft.

### G6 — Catastrophic failure rate at or below a strict justified ceiling

With the 60-pair Tier-1 corpus: **≤ 2% of all scored pairs may trigger any confirmed `C1`–`C11` code — at n=60, this is at most 1 pair** (`floor(0.02 × 60) = 1`), stated as an integer count specifically so the ceiling is not a fractional value with rounding ambiguity. **Zero (0)** confirmed safety-critical events (`C1`, `C2`, `C4`, `C6`, `C9_CONFIRMED`) are permitted on the 18-pair Tier-1 holdout subset. Any non-zero near-tolerance `C7`/`C8`/`C10` event (non-safety-critical) requires explicit PM sign-off before P1 can proceed — it is not an automatic pass merely because it is within the ≤1-pair ceiling.

### G7 — No human-veto catastrophic failures hidden by aggregate averages

`HUMAN_VETO` rate ≤ 2% overall (≤ 1 of 60 pairs), **0** on the 18-pair Tier-1 holdout subset — computed and reported identically to `G6`, never folded into a mean score that could mask a single broken pair.

### G8 — Reproducible Tier-1 results

Re-running the full Tier-1 evaluation pipeline against the same pinned engine commit and the same fixture manifest must reproduce identical objective-metric values (or fall within a documented, justified tolerance for any inherently non-deterministic step, e.g., a stochastic model component) — a reproduction command/checklist must exist and be exercised at least once before a `PASS` claim.

Apple Music AutoMix / djay / Offtrack / Spotify / rekordbox are **stretch references** — P0 need not beat every commercial product on Tier-2, but any benchmark report produced under this contract must state the observed gap against each honestly (per §5.2), not omit or soften it.

## 12. Stop / re-scope conditions

`RE-SCOPE` or `STOP` should be triggered if evidence, once this contract is executed against a real prototype, shows any of:

- Cue/downbeat/phrase work does not materially improve over SimpMusic-class behavior on the P1-gate metrics (`G2`) despite implementation effort — i.e., the hypothesized advantage does not survive contact with measurement.
- Quality remains substantially behind existing easy-to-use commercial products (Offtrack, djay — the two products `PROJECT_CHARTER.md` explicitly requires a wedge against) with no compensating advantage on the product/UX axis.
- Real-time analysis is too computationally expensive for the target hardware (Windows-first per `PROJECT_CHARTER.md`, later Android/iOS/macOS) to run inside a consumer listening app rather than a batch/offline tool.
- Quality collapses outside a narrow genre set (§10 anti-overfitting failure — e.g., the system passes on EDM/4-4 material but fails broadly on the required coverage set).
- The confidence-aware fallback mechanism (`G4`) cannot reliably suppress catastrophic mixes — i.e., confirmed `C11` and `HUMAN_VETO` rates stay materially above the `G6`/`G7` ceilings even after tuning on the development split.
- A required product capability's technical viability turns out to depend on provider integration that is legally unavailable (per `AGENTS.md` rules 3/6/7 — this benchmark contract itself introduces no such dependency, but its future execution against Tier-2 baselines must not either).
- Existing permissive open components (e.g., CUE-DETR + All-In-One + Signalsmith Stretch, per `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) already solve nearly everything this benchmark measures with no defensible improvement opportunity for a custom planner — in that case the correct move is integration, not reinvention, and P0-M3 should say so rather than proceeding to a from-scratch P1.

## 13. Scope discipline

- This document and its companions are **specification/research artifacts only**. No AutoMix engine implementation and no audio fixtures are included or authorized by this task. Per R8, disposable/benchmark-execution prototyping is explicitly in scope for a future P0-M3 task (§2); the shipping production engine is not.
- Every capability/behavior claim about a third-party system in §5 is either sourced from `docs/research/P0-M0-MARKET-PRIOR-ART-LANDSCAPE.md`'s already-cited first-party documentation, or explicitly marked `UNKNOWN_NEEDS_RUNTIME_PROOF` — no proprietary internals are invented, per `AGENTS.md` non-negotiable rule 1 and Issue #4's "Never invent proprietary internals" instruction.
- P0-M3 is explicitly **not started** by this deliverable.

## 14. Acceptance criteria check

See the `HANDOFF TO PM — REPAIR PASS` section of the PM-facing report (not duplicated here) for the line-by-line AC check against Issue #4's acceptance criteria list, and for the R1–R9 repair-item-by-repair-item evidence trail.
