# P0-M2-R1 — AutoMix Quality Benchmark Contract

Status date: 2026-08-11

## 0. Execution profile actually used

- **Execution agent:** Claude Code (Claude Agent SDK CLI).
- **Parent model:** `claude-sonnet-5`, matching the model pinned in Issue #4.
- **Reasoning effort:** Issue #4 states High is owner/PM-attested from the Claude Desktop UI and explicitly instructs the runtime not to treat non-introspectability of that dial as a stop condition. Extended thinking was engaged throughout. This is recorded as an **assumption carried per explicit task instruction**, not a silent pass — see `docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §0/§14 for the prior occurrence of the same limitation and the PM's disposition of it.
- **Dynamic workflows:** OFF.
- **Sub-agents:** OFF — no `Agent`/`Task` subagents were used; all reading, cross-referencing, and writing in this deliverable were performed directly by the parent agent.
- **Fallback policy:** not triggered.
- **Execution-surface note:** Issue #3 (`[SUPERSEDED]`, closed) required Claude Desktop only. Issue #4 explicitly supersedes it; the supersession comment on Issue #3 and Issue #4 itself were independently confirmed authored by `PNHD`, the repository's sole admin collaborator, giving a coherent rationale (the Desktop-provenance gate was unfalsifiable from inside the runtime and caused false `BLOCKED_MODEL_SELECTION` results). This is recorded here for PM auditability, not as a request for re-approval.

## 1. Result

**PARTIAL**

Rationale: this is a specification/research deliverable, not an implementation. Every required section below (benchmark lanes, baselines/comparability, corpus tiers, objective metrics, human rubric, catastrophic failures, anti-overfitting, P0→P1 gate, stop/re-scope conditions) is present with concrete, checkable content. It is scored PARTIAL rather than PASS because:

1. No AutoMix engine or baseline implementation exists yet to run this contract against — every threshold below is a **proposed, principled initial number**, explicitly not validated against real measurement data, and Issue #4 itself requires "do not choose thresholds merely to make future code pass."
2. Several comparability classifications for third-party products (§5) are marked `UNKNOWN_NEEDS_RUNTIME_PROOF` pending hands-on verification that no task in this scope authorized (this is a specification task, not a hands-on competitive test pass — that hands-on pass belongs to the execution of this contract, which is future work, not P0-M2-R1 itself).
3. The optional benchmark pair catalog (`docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`) specifies representative adversarial cases per lane but does not (and per the task's Tier-1 policy, cannot) include actual audio — fixture generation/production is future work.

None of these gaps block PM review of the contract's completeness; they are the expected state of a benchmark *specification* prior to any execution pass.

## 2. Purpose

Define the benchmark contract that decides whether AutoMix is musically better than naive crossfade / BPM-key-only mixing, and whether P1 (local AutoMix engine implementation) is allowed to start. This document, its companion manifest schema (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`), and the optional pair catalog together are the full P0-M2-R1 deliverable set. No AutoMix engine code, no audio files, and no P0-M3 analyzer work are included.

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

A good engine must be able to decide that a complex DJ blend is the wrong transition for a given pair. This benchmark scores that decision explicitly (Lane E, §4.5) rather than assuming "more DSP processing is always better."

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

Each lane is scored independently; a single aggregate score is explicitly disallowed (an engine that is excellent at Lane C and catastrophic at Lane A must not have that catastrophe averaged away). Every case type below must have at least one corresponding fixture/pair in the manifest (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §"pair" object, field `benchmark_lane` + `case_tags`); concrete representative pairs are enumerated in `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`.

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

### 4.2 Lane B — Content collision

vocal→vocal · sustained vocal outro→vocal intro · dense bass→dense bass · percussion-heavy overlap · instrumental→vocal · sparse→dense · dense→sparse.

Rationale: P0-M1 §8 level 6 and §10 confirm SimpMusic has zero vocal/bass/percussion activity signal; its only "content-aware" behavior is a generic DJ-filter EQ sweep applied identically regardless of whether a real collision exists. This lane must contain pairs where a generic EQ sweep is *not* enough to avoid an audible collision, to distinguish "has an EQ effect" from "detects and avoids collisions."

### 4.3 Lane C — Energy / loudness

high→high · low→high · high→low · gradual buildup/drop · large mastering-loudness differences · locally quiet transition region despite high integrated loudness.

Rationale: P0-M1 §9/§10 confirms SimpMusic has exactly one loudness datum per track (a static integrated-loudness gain, applied outside the crossfade planner, not a time-varying contour). The "locally quiet transition region despite high integrated loudness" case specifically defeats any system using only integrated/track-level loudness, since it requires the *transition-window* loudness, not the whole-track average.

### 4.4 Lane D — Harmonic / tempo

compatible key + close tempo · compatible key + large tempo gap · incompatible key + close tempo · half/double-time cases · pitch shifting helps · pitch shifting should be avoided · stretch within reasonable range · stretch outside reasonable range.

Rationale: this lane is where a naive system is *most* likely to look competent (Camelot-wheel key scoring and half/double-time BPM normalization are both things SimpMusic already does correctly per P0-M1 §6, §11). The adversarial value here is in the boundary cases — tempo gaps and key incompatibilities specifically *outside* the range any bounded correction can fix (P0-M1 §10: SimpMusic's own ±25% BPM-ratio and ±2-semitone pitch bounds are evidence the authors know unbounded correction is unsafe, but tracks outside those bounds get *zero* correction, not a smarter decision) — this benchmark must confirm whether a system under test recognizes "this pair is outside safe correction range" and falls back, versus forcing a broken correction or ignoring the mismatch entirely.

### 4.5 Lane E — Confidence / fallback

Corpus must contain pairs where the expected preferred behavior is one or more of:

- `FULL_DJ_BLEND`
- `SHORT_EQ_BLEND`
- `SIMPLE_CROSSFADE`
- `GAPLESS`
- `CUT`
- `NO_SPECIAL_TRANSITION`

This lane scores whether the **chosen transition class** was appropriate, not only whether DSP execution was smooth — a technically flawless DJ blend applied to a pair that should have been a clean cut (e.g., sequential tracks from the same album/continuous mix, per P0-M0 §13's "sequential album tracks where transition may intentionally be suppressed" case) is a failure under this lane even if every other metric is clean. P0-M1 §8 level 8 and §13 confirm SimpMusic has no per-pair transition-style fallback at all (`djCrossfadeEnabled`/`crossfadeEnabled` are static global user settings) — this is the single gap this lane is designed to expose.

## 5. Required baselines and comparability

### 5.1 Comparability classes

| Class | Meaning |
|---|---|
| `IDENTICAL_AUDIO_COMPARISON` | Same audio bytes/master run through both systems |
| `SAME_MASTER_LIKELY` | High confidence of the same master (same catalog release, same provider-reported duration/ISRC) but bytes not independently verified identical |
| `CATALOG_EQUIVALENT` | Same catalog track (title/artist/ISRC where available) but different provider/encode/master is plausible or confirmed |
| `NON_IDENTICAL_SOURCE_LIMITATION` | Comparison is on a materially different source (different remix/edit/live version, or provider forced substitution) |
| `SUBJECTIVE_REFERENCE_ONLY` | System cannot be run on our fixtures at all (closed catalog, no local-file import); scored as an observational quality reference only |

### 5.2 Baseline systems

| # | System | Tier-1 (synthetic/local fixtures) | Tier-2 (commercial listening set) | Comparability | Notes / verification required |
|---|---|---|---|---|---|
| 1 | Fixed-duration equal-power crossfade | Our own reference implementation on Tier-1 audio | N/A | `IDENTICAL_AUDIO_COMPARISON` | Deterministic reference; see §6.1 |
| 2 | Clean cut / gapless | Our own reference implementation on Tier-1 audio | N/A | `IDENTICAL_AUDIO_COMPARISON` | Deterministic reference; see §6.1 |
| 3 | Pinned SimpMusic AutoMix | If local-file playback is confirmed possible, run Tier-1 fixtures directly | Yes, via YouTube-resolved / Tidal-metadata-matched playback | Tier-1: `IDENTICAL_AUDIO_COMPARISON` if local import confirmed, else `NON_IDENTICAL_SOURCE_LIMITATION`. Tier-2: `CATALOG_EQUIVALENT` (Tidal-matched metadata against a YouTube-resolved stream is not guaranteed to be the same master, per P0-M1 §10's metadata-confidence-risk finding) | Score Auto-duration mode with DJ mode **on** and **off** separately, per P0-M1 §15 |
| 4 | Echo Music AutoMix beta | `UNKNOWN_NEEDS_RUNTIME_PROOF` whether local files can be loaded | Not established | Default `NON_IDENTICAL_SOURCE_LIMITATION` until local-file capability is confirmed | P0-M0 §7.1 traced its beat-analysis code but not its file-source capability |
| 5 | Apple Music AutoMix | Cannot run Tier-1 (closed catalog, no local import) | Yes | `SUBJECTIVE_REFERENCE_ONLY` for structure; `CATALOG_EQUIVALENT` at best for Tier-2 (Apple's own masters) | Observable behavior only; never infer internals (P0-M0 §2) |
| 6 | Spotify playlist mixing `Auto` | Cannot run Tier-1 | Yes | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Same constraint |
| 7 | Algoriddim djay Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` — djay documents local-library support; not verified in this task | Yes, via Spotify/Apple Music integration | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON` pending verification; Tier-2 `CATALOG_EQUIVALENT` | djay is the primary licensed-integration benchmark per P0-M0 §4 |
| 8 | Offtrack | Cannot run Tier-1 (provider-only per P0-M0 §3, no confirmed local import) | Yes, via Spotify/Apple Music/SoundCloud | `SUBJECTIVE_REFERENCE_ONLY` / `CATALOG_EQUIVALENT` | Primary consumer benchmark per P0-M0 §3 |
| 9 | rekordbox Automix | `UNKNOWN_NEEDS_RUNTIME_PROOF` — rekordbox is local-library-centric by design, so Tier-1 is plausible | Yes, via Spotify Automix (7.2.16+) | Tier-1 potentially `IDENTICAL_AUDIO_COMPARISON` pending verification; Tier-2 `CATALOG_EQUIVALENT` | Professional reference, benchmark "where practical" per Issue #4 |
| 10 | Future AutoMix engine revisions | Full Tier-1 corpus, every version | N/A | `IDENTICAL_AUDIO_COMPARISON` by construction | This is the internal regression-testing baseline; every future engine change is scored against the same pinned fixture set |

No proprietary internals are invented for #4–#9 anywhere in this contract or its companions; only publicly observable behavior, first-party documentation (already cited in P0-M0 §2), and — where marked `UNKNOWN_NEEDS_RUNTIME_PROOF` — behavior that must be hands-on verified before that system can be scored, not assumed.

## 6. Corpus design (summary — full schema in companion document)

Two tiers, per Issue #4 and `AGENTS.md` non-negotiable rule 4.

### 6.1 Tier 1 — reproducible public/local fixtures

- Allowed sources: synthetic, owner-created, public-domain, CC0, permissively reusable audio only.
- Every fixture records provenance/license/checksum (full field list in the manifest schema).
- No copyrighted commercial audio in Git. No DRM/protected-stream extraction. No provider session material.
- Synthetic fixtures are the primary mechanism for exact ground truth (beat-phase offset, downbeat grid, phrase boundaries, vocal intervals, bass/percussion windows, loudness/energy envelopes) because they are the only way to obtain `SYNTHETIC_EXACT`-grade annotations (§ manifest schema, source enum) with zero measurement error — this is what makes Lane A/B/C/D adversarial cases falsifiable rather than merely plausible.
- Tier-1 is split into a **development/tuning set** and a **holdout acceptance set** (§9.3). Baselines #1, #2, and #10 in §5.2 run on all of Tier-1; baselines #3–#9 run on Tier-1 only where local-file import is confirmed.

### 6.2 Tier 2 — private real-world listening set

- Commercial tracks referenced by metadata/provider IDs only. No audio committed or redistributed.
- Used for subjective, hands-on comparison against baselines #3–#9 in their native/streamed configuration.
- Kept separate from the development/holdout split — Tier-2 is never used to tune Tier-1-facing thresholds, and Tier-1 objective-metric thresholds are never inferred from Tier-2 listening sessions.

## 7. Objective metrics

Every metric below is tagged `OBJECTIVE`, `PROXY`, or `HUMAN_ONLY` per `.agents/skills/automix-task-contract/SKILL.md`'s evidence-gate discipline: `OBJECTIVE` metrics are computed deterministically from ground-truth annotations or the transition-window waveform with no subjective judgment; `PROXY` metrics stand in for a perceptual quality that cannot be measured directly and must be validated against the human rubric (§8) before being trusted alone; `HUMAN_ONLY` has no defensible automated substitute.

| Metric | Formula / method | Unit | Required ground truth | Interpretation | Threshold/range | Limitation | Class |
|---|---|---|---|---|---|---|---|
| Beat alignment error | `min(\|t_actual − t_nearest_grid_beat\|, beat_period − \|...\|)` at the chosen transition anchor point | ms and beat-fraction (`error_ms / beat_period_ms`) | Beat timestamps (`SYNTHETIC_EXACT` preferred) for both tracks | Lower is better; 0 = perfectly on-beat | Target ≤ 1/16 beat (6.25%) for pairs where the system declared beat-synced execution | Meaningless for tracks with no reliable beat grid (weak-beat/rubato material) — mark `N/A`, do not impute 0 | `OBJECTIVE` (when ground truth is `SYNTHETIC_EXACT`/`MANUAL`); `PROXY` when ground truth is `MODEL_ESTIMATE` |
| Downbeat/bar-phase error | Circular distance, in beat positions, between the incoming track's landing beat and the nearest downbeat of the bar grid it entered | integer beat positions (0 = correct bar) | Downbeat/bar-start annotations | 0 = correct bar phase | Target: 0 for pairs where the system declared bar-synced execution | Requires a defined meter; `N/A` for ambiguous-meter fixtures (recorded explicitly, per Lane A) | `OBJECTIVE` |
| Cue-region error | Distance from chosen entry/exit point to the nearest edge of the nearest annotated acceptable region; 0 if inside a region | ms | Acceptable entry/exit region annotations | 0 = inside an annotated-good region | Target: 0 for ≥ 90% of "clean structure" Lane A pairs (see §10) | Acceptable regions are themselves `MANUAL` or `MODEL_ESTIMATE` in non-synthetic material — record source | `OBJECTIVE` for `SYNTHETIC_EXACT`/`MANUAL` regions; `PROXY` otherwise |
| Phrase-boundary distance | `min(\|t − nearest_phrase_boundary\|)` | ms | Phrase-boundary annotations | Lower is better | No universal target; scored per-pair against the fixture's declared `expected_transition_class` | Phrase boundaries in non-synthetic material are frequently `MODEL_ESTIMATE`; do not treat as exact | `OBJECTIVE` (`SYNTHETIC_EXACT`/`MANUAL`); `PROXY` (`MODEL_ESTIMATE`) |
| Section-boundary distance | Same method as phrase-boundary, against section annotations | ms | Section boundary/label annotations | Lower is better where a section-aware entry/exit was expected | Scored per-pair | Section labels are coarser and less reliable than phrase boundaries even for `MANUAL` annotation — always record annotator confidence | `PROXY` |
| Vocal overlap duration/ratio | Sum of ms where both tracks' vocal-activity intervals are simultaneously active within the transition window; ratio = overlap / transition-window duration | ms and ratio [0,1] | Vocal activity intervals | Lower is better for non-intentional collisions | See C4 (§9) for the catastrophic threshold | Vocal-activity ground truth for real material is usually `MODEL_ESTIMATE` (a vocal-activity detector) unless `MANUAL`-annotated; never `SYNTHETIC_EXACT` except for synthetic fixtures with a scripted "vocal-band" stem | `OBJECTIVE` (synthetic); `PROXY` (real material) |
| Bass-overlap proxy | Co-occurrence of two tracks' sub/low-band (defined as 20–150 Hz) short-term RMS energy both exceeding a fixture-relative activity threshold, integrated over the transition window | ms and ratio [0,1] | Bass/percussion activity intervals, or raw low-band energy if intervals are unavailable | Lower is better | See C5 (§9) | This is explicitly a **proxy** — RMS co-occurrence is not the same as perceptual masking, which also depends on spectral overlap, not just band energy; do not present this as a measured masking amount | `PROXY` |
| Short-term loudness delta | `\|LUFS_short_term(t_post) − LUFS_short_term(t_pre)\|` per ITU-R BS.1770 momentary/short-term loudness, measured immediately before and after the transition's committed point | LU | None beyond the audio itself (computed, not annotated) — loudness envelope annotation is used as an independent cross-check, not a requirement | Lower is better | See C6 (§9) for the catastrophic threshold; target ≤ 2 LU for non-catastrophic pairs | Short-term loudness windows (400 ms per BS.1770) can straddle genuinely intentional dynamic content; always inspect alongside the waveform, not as a lone pass/fail | `OBJECTIVE` |
| Transition-window loudness discontinuity | Maximum instantaneous derivative of the short-term loudness curve across the transition window, compared against the same track's typical (non-transition) loudness-derivative baseline | LU/s | None beyond the audio | Lower relative-to-baseline is better | See C6 | Sensitive to fixture length/dynamics; always report relative to the track's own baseline, not an absolute cross-track number | `OBJECTIVE` |
| Energy-continuity delta/slope | Difference between the pre-transition RMS-energy trend slope and the post-transition RMS-energy trend slope, fit over a fixed window (default 4 s each side, configurable per fixture) | dB/s difference | None beyond the audio | Smaller discontinuity in slope is better | No universal target; scored per Lane C case type (e.g., "gradual buildup/drop" expects a *specific* nonzero slope match, not zero) | RMS-energy slope is a coarse proxy for perceived "momentum"; does not capture spectral energy shifts | `PROXY` |
| Applied tempo ratio / max deviation | Ratio of executed playback rate to the track's native tempo at each point in the transition; report both the target ratio and observed max instantaneous deviation from it | ratio (dimensionless), max deviation in % | None beyond engine-reported/measured playback rate | Closer to 1.0 (or to the intentionally chosen ratio) is generally safer | See C7 (§9) | Ratio alone does not capture stretch-algorithm artifact quality — always pair with the human DSP-smoothness rating (§8) | `OBJECTIVE` |
| Pitch shift in semitones | `12 · log2(f_shifted / f_original)` | semitones | None beyond engine-reported/measured pitch shift | Smaller magnitude is generally safer | See C8 (§9) | Same caveat as tempo ratio — pair with human rating | `OBJECTIVE` |
| Click/pop/discontinuity/dropout proxy | Detector flags sample-domain waveform discontinuities (magnitude of second difference exceeding a defined multiple of the local noise floor) at/near the splice or commit boundary, and flags any silence/zero-buffer run inconsistent with the source material | count + timestamps | None beyond the audio | 0 flags is the target | See C9 (§9) | A heuristic detector; false positives on genuinely percussive/transient material are expected — always cross-check against the human rubric before counting a flag as a real defect | `PROXY` |
| Clipping / true-peak | True-peak level per ITU-R BS.1770-4 oversampled true-peak measurement across the transition window | dBTP | None beyond the audio | Target ≤ −1 dBTP | Flag any sample ≥ −1 dBTP | Only relevant where the engine applies gain (loudness compensation, DJ-filter gain); not relevant to pure pass-through segments | `OBJECTIVE` |
| Transition duration | Wall-clock duration of the executed transition window, as actually scheduled by the system under test | ms | None beyond engine-reported/measured timing | Reported, not judged in isolation | Compared against the fixture's `acceptable transition classes` (short vs. long implied by class) | A short duration is not inherently a defect (e.g., `SIMPLE_CROSSFADE`/`CUT` are expected to be short) — always interpret alongside transition-class correctness | `OBJECTIVE` |
| Transition-class correctness | Categorical match between the system's chosen transition class and the fixture's `acceptable_transition_classes` set; also reported as a full confusion matrix across the corpus | categorical (match / mismatch) + confusion matrix | `acceptable_transition_classes` annotation (§ manifest schema) | Match is better | See §10 (P1 gate) for the required match-rate threshold | "Acceptable" is deliberately a *set*, not a single class, for pairs with more than one musically valid choice; a mismatch against a single-member set is a stronger signal than against a multi-member set — report both | `PROXY` (the acceptable-class set is itself `MANUAL`/`SYNTHETIC_EXACT` by design, not a measured ground truth of "the one correct answer") |

## 8. Human listening rubric

Human listening is **mandatory** and has **veto authority** over any automated PASS. No pair may be marked as passing on the strength of objective/proxy metrics alone if a human listener flags it as broken.

### 8.1 Scale

Anchored 1–5 scale (not an unexplained 1–10, per Issue #4):

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
16. Preference vs. baseline (paired comparison against fixed equal-power crossfade, §5.2 #1)

Plus one free-text field for a **veto flag**: `CATASTROPHIC_FAILURE_OBSERVED: yes/no + code (§9) + free-text note`. This is independent of the 1–5 scores — a listener can rate dimension 15 a "2" without invoking veto, but any veto invocation forces the pair to `FAIL` regardless of every other score (§9).

### 8.3 Procedure

- **Blinded/randomized**: listeners are not told which system (baseline, SimpMusic, AutoMix candidate, etc.) produced a given transition; playback order and system identity are randomized per session and logged separately from the listener-facing session.
- **Single-owner procedure (initial)**: the project owner conducts blinded sessions using a randomized playback queue generated from the manifest; system identity is revealed only after all scores for a session are recorded, never during.
- **Multi-rater procedure (later)**: additional listeners score the same blinded queues independently; report inter-rater agreement (e.g., Krippendorff's alpha or simple pairwise agreement rate) per dimension once ≥ 2 raters exist. Do not average away persistent disagreement — report the distribution, not just the mean, when raters diverge by ≥ 2 points on any dimension.
- Every human-rated pair must record: rater ID (or "owner" for the single-rater phase), session timestamp, playback order position, and whether the rater was blinded successfully (self-reported — did they guess the system?).

## 9. Catastrophic failures

Any code below triggers an automatic pair-level `FAIL`, independent of aggregate metric averages, and counts toward the catastrophic-failure-rate gate in §10. A human listener's veto flag (§8.2) can also independently trigger `FAIL` even if no automated detector fired, and is logged as `HUMAN_VETO` alongside any code that also fired. Conversely, an automated code firing is never silently downgraded — a human reviewer may annotate a firing as a false positive, but that annotation and its justification are recorded in the result log, not used to delete the event.

| Code | Definition | Threshold / detection | Gate consequence |
|---|---|---|---|
| `C1_BEAT_TRAINWRECK` | Sustained audible beat drift on a pair the system declared beat-synced | Beat-alignment error > 1/8 beat (12.5%) for > 50% of the overlap window, on pairs with `SYNTHETIC_EXACT`/`MANUAL` beat ground truth and BPM gap ≤ 3% | Pair `FAIL`; counts toward "safety-critical" catastrophic rate (§10) |
| `C2_BAR_PHASE_ERROR` | Wrong beat-in-bar landing on a bar-synced pair | Downbeat/bar-phase error > 0 beat positions when the system declared bar-synced execution and meter/downbeat ground truth exists | Pair `FAIL`; safety-critical |
| `C3_WRONG_PHRASE_LOCATION` | Entry/exit lands outside any acceptable region and more than one full phrase (or 8 bars, where phrase is unknown) from the nearest boundary | Cue-region error exceeds the phrase/8-bar distance, for `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` classes only | Pair `FAIL` |
| `C4_SEVERE_VOCAL_COLLISION` | Two independently active (non-intentional) vocal lines overlap heavily | Vocal-overlap ratio > 60% **and** overlap duration > 4 s | Pair `FAIL`; safety-critical |
| `C5_SEVERE_BASS_MASKING` | Full-energy bass-on-bass collision in a short transition | Bass-overlap proxy > defined high-co-activity threshold for > 50% of a transition window shorter than 4 s | Pair `FAIL` |
| `C6_GROSS_LOUDNESS_DISCONTINUITY` | Audible loudness jump at or during the transition | Instantaneous short-term loudness jump > 6 LU within any single 400 ms window, or > 3 LU step at a `CUT`/`GAPLESS` splice boundary | Pair `FAIL`; safety-critical |
| `C7_STRETCH_ARTIFACT` | Tempo correction pushed far enough to produce an audible artifact | Applied tempo-ratio deviation exceeds the fixture's defined safe envelope **and** human DSP-smoothness rating ≤ 2 | Pair `FAIL` |
| `C8_PITCH_ARTIFACT` | Pitch correction produces an audible artifact | Pitch shift > 3 semitones, or any shift paired with human pitch/key-naturalness rating ≤ 2 | Pair `FAIL` |
| `C9_CLICK_POP_DROPOUT` | Audible discontinuity or dropout at/near the splice/commit boundary | Click/pop/discontinuity detector fires above threshold, or a silence/zero-buffer run inconsistent with source material is detected | Pair `FAIL`; safety-critical |
| `C10_WRONG_METADATA_POISONING` | Engine's BPM/key input diverges from fixture ground truth and measurably drives a bad decision | Input BPM off by > 3 (non-half/double-time-equivalent) or input key off by > 1 Camelot step from `SYNTHETIC_EXACT`/`MANUAL` ground truth, **and** this is traceable to the resulting timing/class decision | Pair `FAIL`; directly tests the exact failure mode P0-M1 §10 identifies as SimpMusic's single largest correctness risk (Tidal duration-matched metadata poisoning) |
| `C11_FORCED_WRONG_TRANSITION_STYLE` | Engine ignored an explicit low-confidence/incompatible signal, or the reverse | System executed `FULL_DJ_BLEND`/complex blend on a pair whose `acceptable_transition_classes` is `{CUT, GAPLESS, NO_SPECIAL_TRANSITION}` only, or forced `NO_SPECIAL_TRANSITION`/`CUT` on a pair with strong compatible signals and no system-declared low-confidence reason | Pair `FAIL`; directly tests Lane E (§4.5) |

"Safety-critical" codes (`C1`, `C2`, `C4`, `C6`, `C9`, plus any `HUMAN_VETO`) require a **zero** occurrence rate on the Tier-1 holdout split for the P1 gate (§10) — these are the failure modes that make a transition *unlistenable*, as distinct from merely suboptimal.

## 10. Anti-overfitting

The benchmark must not be EDM/4-on-the-floor-only — this is the same trap P0-M0 §7.2/§7.4 flags for both `AI-DJ-Mixing-System` (fixed-beat-count phrase/bar proxies) and CUE-DETR (EDM-heavy training domain that "may generalize poorly to pop/hip-hop/rock/non-4/4 material").

- Coverage plan: pop, hip-hop, R&B, rock, electronic, acoustic, ballad, dynamic-tempo/live material where legally obtainable, unusual intros/outros, and non-4/4 cases where musically appropriate.
- Every lane (§4) must have representation outside 4/4 EDM-style material once the corpus matures beyond its initial synthetic seed set; the pair catalog (`docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`) tracks genre/style tag distribution explicitly so this can be audited, not assumed.
- **Holdout pairs/categories may not be hand-tuned.** Any threshold, heuristic, or fixture adjustment made in response to a specific holdout pair's result invalidates that holdout pair — it must be either retired from holdout (and replaced) or the tuning must be reverted. This rule exists specifically so P1-gate numbers (§11) cannot be gamed by iterating against the holdout set.

## 11. P0 → P1 gate

P1 (local AutoMix engine implementation) remains **BLOCKED** until a future provider-independent prototype demonstrates **all** of the following. These are proposed initial numbers grounded in standard practice for paired-preference testing and in the specific gaps P0-M1 documents; they are explicitly not tuned against any existing implementation (none exists) and must not be loosened later merely to make a specific candidate pass — any change requires a PM-reviewed rationale recorded in a future document, not a silent edit here.

1. **Materially better blind human preference than fixed-duration equal-power crossfade** (§5.2 #1): mean paired-preference (rubric dimension 16, §8.2) win rate ≥ 65% with binomial-test significance p < 0.05 across ≥ 40 paired comparisons on Tier-1 dev+holdout combined, **and** ≥ 60% win rate on the holdout split alone.
2. **Materially better quality/preference than pinned SimpMusic** on comparable cases (§5.2 #3, run with Auto+DJ mode on, its most feature-complete configuration per P0-M1 §15): mean overall-preference (rubric dimension 15) ≥ SimpMusic's own score + 0.5 on the 1–5 anchored scale, on the same fixture set run through both systems, n ≥ 30, holdout pairs included.
3. **Real beat/downbeat/cue/phrase-aware behavior, not `60000/BPM` theoretical grids**: on Lane A "clean structure" fixtures with `SYNTHETIC_EXACT` ground truth, median beat-alignment error ≤ 1/16 beat (6.25%) and median downbeat/bar-phase error = 0 for pairs where the system declares beat/bar-synced execution; entry/exit point falls inside an annotated acceptable region in ≥ 90% of those pairs (deliberately-adversarial "no clean intro/outro" pairs are excluded from this specific threshold by design, since forcing a clean-region landing on them is the wrong behavior — see §4.1).
4. **Confidence-aware fallback that sometimes intentionally chooses a simpler transition**: on Lane E fixtures, transition-class match rate (against `acceptable_transition_classes`) ≥ 80% overall, **and** `C11_FORCED_WRONG_TRANSITION_STYLE` rate = 0% on the Lane E "should-not-full-blend" adversarial subset specifically.
5. **Success on unseen holdout pairs**: every threshold above (1–4) must hold independently on the holdout split — not only on the development/tuning split — with no pair-specific tuning permitted on holdout (§10).
6. **Catastrophic failure rate at or below a strict justified ceiling**: ≤ 2% of all scored Tier-1 pairs (dev+holdout combined) trigger any `C1`–`C11` code; **0%** on the Tier-1 holdout split for the safety-critical codes (`C1`, `C2`, `C4`, `C6`, `C9`). Any non-zero near-tolerance `C7`/`C8`/`C10` event requires explicit PM sign-off before P1 can proceed — it is not an automatic pass.
7. **No human-veto catastrophic failures hidden by aggregate averages**: `HUMAN_VETO` rate ≤ 2% overall, **0%** on Tier-1 holdout, computed and reported identically to the automated catastrophic rate in item 6 — never folded into a mean score that could mask a single broken pair.
8. **Reproducible Tier-1 results**: re-running the full Tier-1 evaluation pipeline against the same pinned engine commit and the same fixture manifest must reproduce identical objective-metric values (or fall within a documented, justified tolerance for any inherently non-deterministic step, e.g., a stochastic model component) — a reproduction command/checklist must exist and be exercised at least once before a PASS claim.

Apple Music AutoMix / djay / Offtrack / Spotify / rekordbox are **stretch references** — P0 need not beat every commercial product on Tier-2, but any benchmark report produced under this contract must state the observed gap against each honestly (per §5.2), not omit or soften it.

## 12. Stop / re-scope conditions

`RE-SCOPE` or `STOP` should be triggered if evidence, once this contract is executed against a real prototype, shows any of:

- Cue/downbeat/phrase work does not materially improve over SimpMusic on the P1-gate metrics (§11 item 2) despite implementation effort — i.e., the hypothesized advantage does not survive contact with measurement.
- Quality remains substantially behind existing easy-to-use commercial products (Offtrack, djay — the two products `PROJECT_CHARTER.md` explicitly requires a wedge against) with no compensating advantage on the product/UX axis.
- Real-time analysis is too computationally expensive for the target hardware (Windows-first per `PROJECT_CHARTER.md`, later Android/iOS/macOS) to run inside a consumer listening app rather than a batch/offline tool.
- Quality collapses outside a narrow genre set (§10 anti-overfitting failure — e.g., the system passes on EDM/4-4 material but fails broadly on the required coverage set).
- The confidence-aware fallback mechanism (§11 item 4) cannot reliably suppress catastrophic mixes — i.e., `C11` and `HUMAN_VETO` rates stay materially above the §11 item 6/7 ceilings even after tuning on the development split.
- A required product capability's technical viability turns out to depend on provider integration that is legally unavailable (per `AGENTS.md` rules 3/6/7 — this benchmark contract itself introduces no such dependency, but its future execution against Tier-2 baselines must not either).
- Existing permissive open components (e.g., CUE-DETR + All-In-One + Signalsmith Stretch, per `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) already solve nearly everything this benchmark measures with no defensible improvement opportunity for a custom planner — in that case the correct move is integration, not reinvention, and P0-M3 should say so rather than proceeding to a from-scratch P1.

## 13. Scope discipline

- This document and its companions are **specification/research artifacts only**. No AutoMix engine implementation, no audio fixtures, and no P0-M3 analyzer/DSP technology evaluation are included or authorized by this task.
- Every capability/behavior claim about a third-party system in §5 is either sourced from `docs/research/P0-M0-MARKET-PRIOR-ART-LANDSCAPE.md`'s already-cited first-party documentation, or explicitly marked `UNKNOWN_NEEDS_RUNTIME_PROOF` — no proprietary internals are invented, per `AGENTS.md` non-negotiable rule 1 and Issue #4's "Never invent proprietary internals" instruction.
- P0-M3 is explicitly **not started** by this deliverable.

## 14. Acceptance criteria check

See the `HANDOFF TO PM` section of the PM-facing report (not duplicated here) for the line-by-line AC check against Issue #4's acceptance criteria list.
