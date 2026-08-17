# P0-M4-R1 — Preservation-First Rescope Contract

Status date: 2026-08-17 (repair pass)

Binding task: PM-authorized "P0-M4-R1 — PRESERVATION-FIRST RESCOPE CONTRACT" specification-bridge task, following the accepted P0-M4 decision `RESCOPE_BEFORE_P1` (`docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md`).

Accepted starting HEAD for the original pass: `a4db362452ebe5a70c41c56943d512f70e57b316` (verified before any edit — see §1).

## R0. Repair pass — binding PM review and scope

This document was repaired once, in the same session/branch, in response to PM review result `RESCOPE_CONTRACT_REPAIR_REQUIRED` (Issue #8 comment id `5316347548`), starting from the previously pushed HEAD `0e2b1091479daa00aee74d3a2f6460278588b7c2` (verified live before this repair — see the repair task's own live-state check, reported in the handoff, not duplicated in this document's §2 which describes the original pass's starting point). This is **one narrow repair pass**, not a redesign: everything accepted in the original pass is retained except where a repair below necessarily touches it. Five repairs, each traceable to its own PM finding:

- **R1** — `NG2` (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16.5) was previously unexecutable because the compact narrow rubric never collected dimension 15; fixed by adding exactly that one scalar, for `NG2` pairs only.
- **R2** — pair selection (§12 below) was previously under-specified/discretionary; replaced with one unique, fully deterministic hash-ranking algorithm.
- **R3** — `PLAY_THROUGH` (a `PlannerDecision.decision_type`) was previously conflated with the P0-M2 rendered `observed_class` taxonomy; the two are now kept explicit and separate everywhere in this contract and in the benchmark contract's `NG4`/`NG6` sections.
- **R4** — `C4`/`C5` (vocal/bass collision) were previously marked unconditionally `APPLICABLE` without a real rendered-audio measurement path; corrected to `CONDITIONAL_WHERE_PREEXISTING_ACCEPTED_EVIDENCE_EXISTS`, currently `UNKNOWN_NOT_MACHINE_CONFIRMED`, with mandatory coverage reporting and no new analyzer installed.
- **R5** — `tools/p0m4/verify_rescope_contract.py` strengthened to mechanically catch all four defects above, plus deterministic self-tests for the R2 selection algorithm using synthetic IDs only.

## 0. Execution profile actually used

- **Execution surface:** Claude Desktop → Code (per `AGENTS.md`/`CLAUDE.md` execution-surface semantics — the embedded runtime self-identifies as a Claude Code runtime, which is explicitly not a stop condition for this surface).
- **Model:** `claude-sonnet-5`. **Reasoning effort:** High (Desktop UI selection, not independently introspectable, per the same non-stop-condition rule used throughout this project's prior accepted reports).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Agent teams:** OFF. **Nested agents:** OFF. **Parallel delegation:** OFF. **Fallback:** NONE, not triggered.
- **Session:** same Claude Desktop → Code session as the original pass, continued for this repair, as required.

## 1. Result

**`RESCOPE_CONTRACT_READY_FOR_PM_REVIEW`** (repair pass; not `NARROW_P1_ENTRY_ALLOWED` — no validation has run)

## 2. Live-state verification (performed before any edit)

| Check | Value | Matches expectation? |
|---|---|---|
| Current branch | `research/p0-feasibility` | yes |
| Local HEAD (session start) | `6a54790d220533eb6c336230fd6df23b98aed155` | behind origin by one commit (see below) |
| `origin/research/p0-feasibility` (after `git fetch`) | `a4db362452ebe5a70c41c56943d512f70e57b316` | **matches the task's expected accepted starting HEAD exactly** |
| Relationship | `git merge-base --is-ancestor 6a54790 a4db362` → true; `git log 6a54790..a4db362` → exactly one commit, `a4db362 docs: synthesize P0 feasibility and rescope gate` (adds `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md` only) | clean fast-forward, not a divergence |
| Action taken | `git pull --ff-only origin research/p0-feasibility` → local HEAD updated to `a4db362452ebe5a70c41c56943d512f70e57b316` | fast-forward only; no rebase, merge, or reset used |
| Working-tree status (before and after the fast-forward) | Only pre-existing untracked files: `HANDOFF_TO_PM.md` and 13 `P0-M3-*-PM-REVIEW.zip` files (local-only PM review packages from prior tasks, never committed) | no modified tracked files; nothing stashed or discarded |
| `main` local | `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` | matches expected `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` exactly |
| `origin/main` | `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` | matches; untouched |

**Interpretation:** the research branch had not moved *past* the expected accepted HEAD — the local checkout was simply one fast-forward commit behind origin, which was already sitting exactly at the task's stated expected HEAD. This is not the `BLOCKED_HEAD_MOVED` condition (that condition is for the branch having advanced *beyond*, or diverged from, the expected HEAD with unknown intervening changes). A `--ff-only` pull is a safe, non-destructive, non-rebase, non-merge, non-reset operation that brings local state into exact agreement with the verified, expected, already-known commit. Work proceeds from `a4db362452ebe5a70c41c56943d512f70e57b316`.

## 3. Read-first material actually read at current HEAD

`AGENTS.md`, `CLAUDE.md`, `.agents/skills/automix-task-contract/SKILL.md`, `.agents/skills/automix-forensic-research/SKILL.md`, `.agents/skills/automix-code-review/SKILL.md`, `docs/PROJECT_CHARTER.md`, `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md`, `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`, `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`, `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`, `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md`, `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md`, `docs/research/P0-M3-R3-FINAL-REAL-CORPUS-REPLAY.md`, `docs/research/P0-M3-R3-ANALYZER-EVIDENCE-RECOVERY.md`, `docs/research/P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE.md`, `docs/research/P0-M3-R3-RM041-RM014-EVIDENCE-STABILITY.md`. The existing R3 renderer was inspected read-only (§9). No audio was decoded or analyzed. No analyzer/oracle/render/provider tool was invoked.

## 4. Scope discipline (binding on this task)

This is **specification/contract work only**. No P1 code, no production engine code, no owner-audio decode/analysis, no render, no listening pack, no rerun of the 100-track corpus, no reopening of the R3 analyzer search, and no provider integration work were performed. Nothing in this document authorizes any of those; it defines the contract a *future* validation task must follow.

## 5. The nine required answers (from current HEAD alone)

### 5.1 What is the only authorized first production scope?

**`PRESERVATION_FIRST_LOCAL_AUTOMIX`**, as recorded in `docs/PROJECT_CHARTER.md`'s "Post-P0 scope decision (P0-M4)" section (added by this task): local/DRM-free audio only, preservation-first, consumer listening (not DJ/highlight playback), simple/no-special transition first, fail-closed. Default-enabled *rendered* classes: `NO_SPECIAL_TRANSITION`, `GAPLESS` only at genuine natural/continuous-work boundaries, `SIMPLE_CROSSFADE` at a preservation-safe near-end boundary; the planner may additionally answer an intermediate query with the non-render decision `PLAY_THROUGH` (§7 below — repair R3 keeps this distinction explicit).

### 5.2 What is explicitly excluded?

`FULL_DJ_BLEND`, tempo/time-stretch automation, pitch/key shifting, beat/downbeat-synchronized overlap as a product promise, automatic song-shortening/highlight playback, automatic non-natural `CUT` as default behavior. `SHORT_EQ_BLEND` is research-only, off by default, and does not become a production default merely because research code for it already exists (`docs/PROJECT_CHARTER.md`, `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md` §13).

### 5.3 What must be validated before P1 may begin?

Two independent conditions, both required:

1. This Charter/benchmark revision (this task's diff) is accepted by the PM.
2. The one bounded real-music preservation-first validation defined in §7–§13 below independently passes every applicable `NG1`–`NG8` threshold (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16), including every holdout component, and terminates with `NARROW_P1_ENTRY_ALLOWED` (§13).

### 5.4 Which old P0-M2 gates remain binding?

`G1`–`G8` (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §12) remain fully intact, unmodified, and binding as the historical gate for the original broad, `FULL_DJ`-capable P1 hypothesis. No numeric value in `G1`–`G8` was changed by this task (verified, §14 item 7).

### 5.5 Which broad/FULL_DJ-specific gates are not applicable to the narrow scope?

`G3` (beat/downbeat/cue/phrase production requirement) is `REPLACED_FOR_NARROW_SCOPE` by `NG3` (preservation/boundary safety). Within the catastrophic-failure taxonomy, `C1_BEAT_TRAINWRECK`, `C2_BAR_PHASE_ERROR`, `C3_WRONG_PHRASE_LOCATION`, `C7_STRETCH_ARTIFACT`, `C8_PITCH_ARTIFACT`, and `C10_WRONG_METADATA_POISONING` are `NOT_APPLICABLE` to the narrow scope; `C4_SEVERE_VOCAL_COLLISION`/`C5_SEVERE_BASS_MASKING` are `CONDITIONAL_WHERE_PREEXISTING_ACCEPTED_EVIDENCE_EXISTS` — currently `UNKNOWN_NOT_MACHINE_CONFIRMED` for every pair pending a genuine rendered-audio implementation, per repair R4 (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16.9's full mapping table).

### 5.6 What exact narrow replacements apply?

`NG1`–`NG8`, defined in full in `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16, summarized in §8 below.

### 5.7 What is the one bounded real-music validation?

50 distinct real-music pairs (28 `dev` / 22 `holdout`) drawn from the existing authorized local/DRM-free owner corpus, selected by the frozen deterministic rule in §12, scored against `NG1`–`NG8` using the existing R2 planner (`docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md`) restricted to the narrow class set and the existing `SIMPLE_CROSSFADE`/fallback rendering paths named in §9 (no new analyzer/oracle/DSP).

### 5.8 What exact result authorizes P1?

`NARROW_P1_ENTRY_ALLOWED` — every applicable `NG1`–`NG8` threshold, including every holdout component, independently satisfied (§13).

### 5.9 What exact result stops/redesigns the project?

`STOP_OR_REDESIGN` — any `NG1`–`NG8` threshold not met. A `STOP_OR_REDESIGN` result does not authorize reopening the R3 analyzer search, adding a new analyzer, relaxing any `NG` threshold, cherry-picking different pairs/songs, or silently falling back to `FULL_DJ_BLEND`/broad-scope claims (§13, "hard finish rule").

## 6. Charter changes (summary — full text is the committed diff)

`docs/PROJECT_CHARTER.md` gained:

1. A new "Post-P0 scope decision (P0-M4)" section (after "Initial target", before "Architecture boundaries") recording the `RESCOPE_BEFORE_P1` decision, naming `PRESERVATION_FIRST_LOCAL_AUTOMIX` as the only authorized first production scope, and explicitly stating that the broad `FULL_DJ`-capable engine remains a long-term research target that does **not** inherit authorization from the narrow P1.
2. A scope note at the top of "Architecture boundaries" clarifying that §3–§5 describe the full long-term target, not a mandatory shipping checklist for the first P1.
3. Per-line **[P1-REQUIRED]** / **[FUTURE / RESEARCH for P1]** annotations added to every item in "3. Analysis engine", "4. Transition planner", and "5. DSP/playback engine" — no line was deleted; the full target schema is preserved verbatim with annotations added alongside it.
4. The "P0 novelty gate" section gained one paragraph recording P0-M4's actual per-condition result (condition 4 `FAIL`, conditions 3/5 `PARTIAL`) and pointing to the redefined P1 phase.
5. "P1 — Local AutoMix Engine" was rewritten with two subsections: the authorized narrow scope (this contract) and "P1-BROAD (long-term research target, not currently authorized)" for the original description, which is preserved, not deleted, and explicitly marked as requiring a separate future PM-approved gate.

Nothing under "Definition of success" was changed — it is a long-term, aspirational statement that does not itself claim P0 already passed audible quality.

## 7. Simple-transition class contract (first production prototype)

**Repair R3 — two different taxonomies, kept explicitly separate:**

- `PlannerDecision.decision_type` (`tools/p0m3/transition_policy/policy/contract.py`) ∈ `{"TRANSITION", "PLAY_THROUGH", "NO_SPECIAL_TRANSITION"}` — a planner-level query answer, not a rendered outcome.
- P0-M2 `observed_class` (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §9 `observed_class` enum) — the classification of an actually-rendered audio join. `PLAY_THROUGH` is not, and never will be, a member of this enum.

**Default-enabled, observable/rendered classes (exactly three):**

| Class | Definition source | Product claim |
|---|---|---|
| `NO_SPECIAL_TRANSITION` | `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1 `observed_class`; also reachable as a `PlannerDecision.decision_type` when the planner has nothing eligible at the natural boundary itself | Zero overlap; no processing. First-class rendered result, not an error state. |
| `GAPLESS` | Only when `is_continuous_work = true` (a genuine natural/continuous-work boundary) — `tools/p0m3/transition_policy/policy/eligibility.py`, `policy/boundary.py` | Zero overlap, sample-contiguous join. |
| `SIMPLE_CROSSFADE` | Volume/gain overlap only, at a preservation-safe near-end boundary selected by the R2 planner | Equal-power crossfade, no beat/downbeat/tempo/pitch claim. |

**`PLAY_THROUGH` — a non-render planner decision, not a fourth class:** when the planner is queried at an intermediate boundary and finds nothing eligible yet, it returns `decision_type = "PLAY_THROUGH"` (`allowed_transition_class_set = []`) and current-track playback simply continues; no audio is rendered at that query point. When playback later reaches the pair's actual natural boundary, the real join is rendered and classified as one of the three observable classes above — ordinarily `NO_SPECIAL_TRANSITION`, or `GAPLESS` only under genuine continuous-work conditions. `PLAY_THROUGH` itself is never scored, never enters a transition-class confusion matrix, and is never counted toward any forbidden-class or class-match tally (§8, `NG4`).

**Excluded from the first production prototype (forbidden `observed_class` values):** `FULL_DJ_BLEND`, tempo/time-stretch automation, pitch/key shifting, beat/downbeat-synchronized overlap as a product promise, automatic highlight/song-shortening mode, automatic non-natural `CUT` as a default behavior.

**Research-only, off by default:** `SHORT_EQ_BLEND` — may remain in the research harness (`dsp/mixing.py`'s bass-handoff/EQ-adjacent machinery) but must not become a product default until a same-boundary real-listening result proves it improves over `SIMPLE_CROSSFADE` without introducing loudness holes or fatigue, per a separate, explicit, future PM-approved gate.

## 8. NG1–NG8 narrow gate (pointer + summary)

Full binding definitions are in `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16. Summary:

| Gate | One-line requirement |
|---|---|
| `NG1` | Blind preference vs. fixed equal-power crossfade: tie ≤20%; combined n≥40 decisive, win rate ≥65%, p<0.05; holdout n≥18 decisive, win rate ≥60%. |
| `NG2` | SimpMusic-class comparison, 30 pairs (21 dev/9 holdout): candidate & comparator each rated dimension 15 (`OVERALL_MUSICAL_INTENTIONALITY`, 1–5); mean candidate dim15 ≥ mean comparator dim15 + 0.5, combined and independently on holdout (repair R1). |
| `NG3` | `outgoing_content_preservation_ratio ≥0.95` every transition; 100% on holdout; `<0.90` is catastrophic and independently blocks entry. |
| `NG4` | Only `NO_SPECIAL_TRANSITION`/`GAPLESS`/`SIMPLE_CROSSFADE` are ever rendered/scored (`PLAY_THROUGH` is a non-render planner decision, never in the confusion matrix — repair R3); 23-pair subset (16 dev/7 holdout); class-match ≥80% overall, ≥6/7 holdout; forbidden-class rate 0/50, 0/22 holdout. |
| `NG5` | Holdout frozen before listening/tuning; no pair-specific tuning; independent pass on every gate's own holdout component. |
| `NG6` | ≤1/50 confirmed catastrophic pair overall; 0/22 holdout; narrowed `C1`–`C11` applicability (§5.5 above); `C4`/`C5` status `UNKNOWN_NOT_MACHINE_CONFIRMED` pending accepted rendered-audio evidence, never zeroed by default (repair R4). |
| `NG7` | ≤1/50 `HUMAN_VETO` overall; 0/22 holdout; compact A/B/Tie + separate veto/reason UX, plus dimension-15 collection for `NG2` pairs only; vetoes counted per-pair across sessions, never double-counted. |
| `NG8` | Reproduction checklist executed once; pinned engine + frozen manifest reproduces identical objective metrics (or documented tolerance). |

Pair selection for the frozen 50, and for the `NG2`/`NG4` subsets within it, follows the one deterministic hash-ranking algorithm in §12 below (repair R2) — no discretionary selection remains anywhere in this contract.

## 9. Existing R3 renderer binding (read-only inspection; nothing invoked or modified)

Every class the narrow scope authorizes already has a reusable, already-existing code path. No new DSP is required, so `BLOCKED_EXISTING_RENDERER_GAP` does not apply.

### 9.1 `SIMPLE_CROSSFADE`

- **Renderer entry point:** [`tools/p0m3/audio_render_shootout/dsp/render_m1.py`](../../tools/p0m3/audio_render_shootout/dsp/render_m1.py)`::render()` — documented in-file as "M1 -- planner-correct equal-power SIMPLE_CROSSFADE reference"; emits `rendered_transition_class: "SIMPLE_CROSSFADE"`, `gain_law: "equal_power"`, `beat_alignment_applied: false`, `applied_tempo_ratio: 1.0`, and deliberately never applies tempo correction or beat alignment even when the planner also permits a more complex class — exactly the "do less" reference this scope needs.
- **Shared DSP it calls:** [`dsp/mixing.py`](../../tools/p0m3/audio_render_shootout/dsp/mixing.py)`::assemble_transition_render(..., use_equal_power=True, use_bass_handoff=False)`, which calls `mix_overlap(curve="equal_power")` → `equal_power_gains()` (constant-power crossfade, public-domain formula, no GPL/Signalsmith code involved) and `apply_headroom_and_safety()` for deterministic clip prevention.
- **Boundary/segment logic it consumes:** [`dsp/render_common.py`](../../tools/p0m3/audio_render_shootout/dsp/render_common.py)`::load_scenario_context()` / `compute_segments()`, which reads the R2 planner's `PlannerDecision` onset/content-end/entry timestamps verbatim (never re-derived or guessed).

### 9.2 `NO_SPECIAL_TRANSITION` / `GAPLESS` (rendered classes), and `PLAY_THROUGH` (non-render planner decision)

These are defined as **zero overlap** by construction (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1: "None" automation). No dedicated audio-mixing DSP is needed or exists for them, and none is missing:

- **Decision layer:** [`tools/p0m3/transition_policy/policy/contract.py`](../../tools/p0m3/transition_policy/policy/contract.py)`::build_fallback_decision()` already produces `decision_type ∈ {"PLAY_THROUGH", "NO_SPECIAL_TRANSITION"}` with the correct `allowed_transition_class_set` (`[]` for `PLAY_THROUGH`, `["NO_SPECIAL_TRANSITION"]` otherwise) — first-class results, not error states (see the `AC10` comment at `contract.py` line 47). Per §7's repair-R3 taxonomy split, only the `decision_type = "NO_SPECIAL_TRANSITION"` and (via the eligibility/selection layer below) `GAPLESS` outcomes are ever scored as an `observed_class`; a `decision_type = "PLAY_THROUGH"` answer at an intermediate query point means no render happened at that point and is not itself an `observed_class`.
- **Eligibility/selection layer:** [`policy/eligibility.py`](../../tools/p0m3/transition_policy/policy/eligibility.py) lines 134/210 and [`policy/boundary.py`](../../tools/p0m3/transition_policy/policy/boundary.py) lines 134/278 already select `GAPLESS`/`NO_SPECIAL_TRANSITION` when no safe near-end candidate exists or when the pair is annotated `is_continuous_work`/`sequencing_suppression_intended`.
- **Rendering, mechanically:** with `overlap_len_smp == 0`, the exact same `dsp/render_common.py::compute_segments()` segment-assembly logic used by `SIMPLE_CROSSFADE` already produces `[outgoing_pre] + [] + [incoming_post]` — i.e. plain concatenation with zero or natural gap. This is a direct, zero-new-code restriction of the existing segment-assembly path, not a missing interface.

**Conclusion:** every one of the three authorized *observable* classes (`NO_SPECIAL_TRANSITION`, `GAPLESS`, `SIMPLE_CROSSFADE`) is renderable using already-existing, already-accepted code, and the non-render `PLAY_THROUGH` planner decision requires no renderer at all by definition. The next validation task must reuse `render_m1.render()` (or the underlying `dsp.mixing`/`dsp.render_common` functions it calls) for `SIMPLE_CROSSFADE`, and plain segment concatenation (zero overlap) for the other two rendered classes — no new DSP, no new renderer file, no analyzer.

## 10. Loudness / safety contract

Carried forward unchanged from the accepted P0-M2 objective definitions (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §8/§10):

- Momentary = 400 ms, short-term = 3 s, ITU-R BS.1770-5 terminology (EBU R128/Tech 3341 window naming).
- `COND_LOUDNESS_OK`: momentary loudness delta ≤2 LU, unchanged.
- `C6_GROSS_LOUDNESS_DISCONTINUITY`: >6 LU momentary jump between consecutive 100 ms-stepped measurements, or >3 LU momentary step at a `CUT`/`GAPLESS` splice — unchanged, still safety-critical, still `APPLICABLE` under the narrow scope (§5.5/`NG6` mapping).

These metrics remain **objective diagnostics** and **catastrophic-failure evidence** (`C6` firing) and **explanatory evidence** for a blind preference/veto outcome. They are never, by themselves, sufficient to authorize P1 — `NG1`'s blind human preference result remains the final proof of actual audible benefit. No new arbitrary loudness threshold was invented to make any gate pass more easily.

## 11. Provider / legal boundary

The narrow validation and the first authorized P1 are **local / DRM-free audio only**. Provider integration (Spotify, Apple Music, YouTube Music, or any other streaming provider) remains **deferred** — it is not part of this scope and is not unlocked by this contract.

Explicitly forbidden, unconditionally: DRM circumvention, protected-stream extraction, cookie/token/session extraction, undocumented provider endpoints, MITM, process injection, memory hooking. Ordinary public Spotify/Apple APIs do not provide the PCM/control surface this engine needs, and no claim to the contrary is made anywhere in this document or the Charter changes.

## 12. Pair selection algorithm (repair R2 — replaces the prior under-specified, discretionary description)

**Defect being repaired:** the prior version of this section described stratification by "duration/loudness/silence/energy bins" combined with "a fixed, pre-registered pseudorandom split" without naming a unique seed, ordering, or tie-break rule — leaving real discretion in which 50 pairs, and which dev/holdout/`NG2`/`NG4` assignment, would actually be produced. This repair replaces it with **one unique, fully deterministic algorithm**. Given the same corpus of opaque track IDs, it produces exactly one 50-pair corpus, exactly one dev/holdout split, and exactly one `NG2`/`NG4` subset assignment — no human choice remains anywhere in it.

The validation uses real local/DRM-free music only, from the existing authorized owner corpus already used by prior R3 tasks (`owner_music_input`, unchanged root, not re-scanned or broadened).

### 12.1 Input

- The approved existing opaque track IDs only (the same opaque `RM###`-style identifiers already used throughout the accepted R3 evidence — never a filename, title, artist, or path).
- Sorted lexicographically before any further step.
- The candidate universe is every ordered pair `(OUT_ID, IN_ID)` with `OUT_ID != IN_ID` (self-pairs rejected).
- No filename/title/artist/path lookup is performed anywhere in this algorithm.

### 12.2 Fixed salt

```
P0-M4-R1-NARROW-VALIDATION-v1
```

This exact literal string is the salt for every hash below. It is fixed in this document, not chosen per-run.

### 12.3 Pair rank key and the 50-pair selection scan

For every candidate ordered pair, compute:

```
PAIR_KEY = SHA256("P0-M4-R1-NARROW-VALIDATION-v1|PAIR|" + OUT_ID + "|" + IN_ID)
```

Sort the full candidate universe ascending by: (1) `PAIR_KEY` hex digest, (2) `OUT_ID`, (3) `IN_ID` (the latter two are pure tie-breaks in the astronomically unlikely event of a hash collision).

Scan this sorted list from the top, accepting a pair into the frozen 50-pair corpus only if all of the following hold at the time it is considered:

- it is not a self-pair (already excluded from the universe, §12.1);
- its reverse (`IN_ID → OUT_ID`) has not already been accepted — the corpus never contains both `A→B` and `B→A`;
- accepting it would not cause any single opaque track to appear in **more than 2** already-accepted pairs, counting both outgoing and incoming roles combined.

Continue scanning deterministically until **exactly 50** pairs are accepted.

**Hard stop, not a soft target:** if the scan reaches the end of the sorted universe with fewer than 50 pairs accepted under these constraints, the future validation task must **stop before rendering** and report the shortfall. The max-2-appearances and no-reverse-duplicate constraints are never loosened automatically to reach 50.

### 12.4 Dev / holdout split

For each of the frozen 50 pairs, compute:

```
SPLIT_KEY = SHA256("P0-M4-R1-NARROW-VALIDATION-v1|SPLIT|" + OUT_ID + "|" + IN_ID)
```

Sort the 50 pairs ascending by `SPLIT_KEY` hex digest. The **lowest 22** become `holdout`; the **remaining 28** become `dev`. (`28 + 22 = 50`, matching §16.3 of the benchmark contract.)

### 12.5 `NG2` subset (30 = 21 dev + 9 holdout)

Within the 22-pair `holdout` set, compute `NG2_KEY = SHA256("P0-M4-R1-NARROW-VALIDATION-v1|NG2|" + OUT_ID + "|" + IN_ID)` for each pair, sort ascending, and take the lowest **9**.

Within the 28-pair `dev` set, compute the same `NG2_KEY` formula, sort ascending, and take the lowest **21**.

Total `NG2` subset: **30** (21 dev + 9 holdout), matching `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16.5 exactly.

### 12.6 `NG4` subset (23 = 16 dev + 7 holdout)

Within `holdout`, compute `NG4_KEY = SHA256("P0-M4-R1-NARROW-VALIDATION-v1|NG4|" + OUT_ID + "|" + IN_ID)` for each pair, sort ascending, and take the lowest **7**.

Within `dev`, same formula, sort ascending, take the lowest **16**.

Total `NG4` subset: **23** (16 dev + 7 holdout), matching `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16.7 exactly. (`NG2` and `NG4` subset membership are computed independently against the same frozen 50 and may overlap; neither is a subset of the other by construction.)

### 12.7 `NG2` backfill on unrenderable pairs

If an `NG2`-selected pair is later found unrenderable on either side under the accepted `IDENTICAL_AUDIO_COMPARISON`/clean-room comparison path (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16.5), it is excluded and logged `NG2_EXCLUDED_UNRENDERABLE`, never silently scored. Its replacement is the next-lowest-`NG2_KEY` pair from the **same** `dev`/`holdout` partition not already selected for `NG2`, checked for renderability in turn. If a partition is exhausted before reaching the required count (9 holdout / 21 dev), the validation task must stop before scoring `NG2` rather than loosen the definition of a valid observation (§16.5).

### 12.8 What may never influence selection

Duration bins, integrated-loudness-difference bins, leading/trailing-silence characteristics, and any other level/energy characteristic may be **computed and reported after selection**, purely as coverage diagnostics. They — and any render/listening/planner result — **must never** change: pair membership, pair direction, the `dev`/`holdout` assignment, the `NG2` subset, or the `NG4` subset. No human-chosen random seed exists anywhere in this algorithm; the only "seed" is the fixed literal salt in §12.2, which is part of this committed document, not a run-time choice.

**Explicitly not used for selection, at any step:** filenames, artist/title identity, any web search of track identities, genre oracle, harmonic oracle, downbeat model, phrase model, structure model, CUE-DETR, or All-In-One. No new analyzer is authorized merely to select friendly validation pairs.

### 12.9 Freeze requirement

The full 50-pair list, `dev`/`holdout` assignment, and `NG2`/`NG4` subset membership (all fully determined by §12.1–§12.8 the moment the input track-ID set is fixed) must be written to a committed-or-sanitized manifest before any render or listening session starts, and never revisited afterward.

### 12.10 Deterministic self-test (no private corpus needed)

`tools/p0m4/verify_rescope_contract.py` (§16 below) implements this exact algorithm against **synthetic** opaque IDs (e.g. `["T01", "T02", ..., "T60"]`) and checks: selection is invariant to the input ID list's original order (only the lexicographic sort in §12.1 matters); a repeated run on the same input produces an identical pair list; no reverse duplicate exists; no track appears more than twice; the split is exactly 22 holdout / 28 dev; the `NG2` subset is exactly 9 holdout + 21 dev; the `NG4` subset is exactly 7 holdout + 16 dev. This proves the algorithm's invariants mechanically, without touching any private/real track ID.

## 13. Next validation contract — hard finish rule

The next task (not this one) executes the validation defined above and must terminate with **exactly one** of two terminal product decisions:

- **`NARROW_P1_ENTRY_ALLOWED`** — every applicable `NG1`–`NG8` threshold, including every holdout component, independently satisfied.
- **`STOP_OR_REDESIGN`** — any threshold not met.

If `STOP_OR_REDESIGN`: do **not** reopen R3, do **not** add another analyzer, do **not** relax any threshold, do **not** cherry-pick different songs, and do **not** silently switch to `FULL_DJ_BLEND`. A failed simple preservation-first validation means the product must stop or be materially redesigned — it is not a signal to reach for more analyzer sophistication.

## 14. Broad research freeze (explicit, unchanged, not deleted)

Frozen for the purpose of narrow-P1 authorization — none of the following may unlock narrow production behavior, though all remain in repository research history:

- `FULL_DJ` gate/evaluator outcomes (`docs/research/P0-M3-R3-FINAL-REAL-CORPUS-REPLAY.md` and predecessors).
- The current real-corpus V1/V2 search.
- All-In-One (`docs/research/P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE.md`).
- CUE-DETR.
- madmom.
- Essentia.
- Harmonic-oracle work (`docs/research/P0-M3-R3-RM041-RM014-EVIDENCE-STABILITY.md`).
- Style/genre calibration.
- Downbeat calibration.
- The Signalsmith tempo path (`dsp/render_m2_signalsmith.py`, `vendor/signalsmith-stretch`).
- The Rubber Band reference path (`dsp/render_m3_rubberband.py`).

No new analyzer/oracle loop is authorized merely because this rescope contract exists.

## 15. Consistency check across current HEAD (post-edit)

Searched the full repository (tracked files) for statements implying: broad `FULL_DJ` P1 is currently authorized; tempo/stretch is mandatory in first P1; pitch shifting is mandatory in first P1; beat/downbeat/phrase/section ML is mandatory in first P1; provider integration is part of first P1; `G1`–`G8` were "waived"; P0 passed audible quality; invalidated owner packs count as quality evidence.

Result: no occurrence of any of these claims exists unqualified at current HEAD. Every place a broad/`FULL_DJ` capability is described, it is either (a) explicit historical research evidence, correctly labeled with its accepted result (e.g. `R3_FINAL_PARTIAL_NO_VALID_V1_V2`, `ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY`), (b) the long-term research target, now explicitly labeled as such and explicitly not inheriting authorization from the narrow P1 (`docs/PROJECT_CHARTER.md`'s new "Post-P0 scope decision" section and the annotated Architecture Boundaries), or (c) corrected by this task's edits. `G1`–`G8` are never described as waived anywhere in the repository; the new `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16 explicitly states they remain historical/binding and are not weakened. Invalidated owner listening packs remain labeled `INVALID_DO_NOT_RATE` in their original reports and are not referenced anywhere in this task's new material as quality evidence.

## 16. Machine-readable consistency verifier

`tools/p0m4/verify_rescope_contract.py` (docs-only checks, no audio/network/model dependency) independently checks, from the original pass:

1. `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` still contains the original, unmodified `G1`–`G8` numeric anchors (`74`, `52`, `22`, `65%`, `60%`, `30`, `21`, `9`).
2. The §16 appendix contains all eight `NG1`–`NG8` headings and the `50`/`28`/`22` corpus arithmetic.
3. The tie-rate arithmetic (`50 - floor(0.20*50) = 40`, `22 - floor(0.20*22) = 18`) is present verbatim.
4. `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md` contains the exact forbidden-class list and the `SHORT_EQ_BLEND`/research-only/off-by-default statement.
5. `docs/PROJECT_CHARTER.md` contains `PRESERVATION_FIRST_LOCAL_AUTOMIX` as the authorized first production scope and explicitly states the broad engine does not inherit authorization from it.
6. None of the tracked `docs/**/*.md` files contain the unqualified prohibited-claim strings listed in §15.

And, added by this repair (R5), independently checks:

7. `NG2` (§16.5 of the benchmark contract) explicitly names dimension 15/`OVERALL_MUSICAL_INTENTIONALITY` and states it is collected for **both** the candidate and the comparator.
8. `NG2`'s `+0.5` threshold is stated as applying independently to all 30 **and** to the 9-pair holdout.
9. The pair-selection algorithm (§12) contains, verbatim: the literal fixed salt `P0-M4-R1-NARROW-VALIDATION-v1`; the `SHA256(...|PAIR|...)` pair-hash rule; the reverse-pair exclusion rule; the max-2-track-appearance rule; the exact figure `50`; the exact `22`/`28` split; the exact `NG2` `9`/`21` split; the exact `NG4` `7`/`16` split.
10. `PLAY_THROUGH` never appears inside this contract's authorized-*observed*-class enumeration (i.e. never listed together with `NO_SPECIAL_TRANSITION`/`GAPLESS`/`SIMPLE_CROSSFADE` as if it were a fourth rendered class).
11. This contract explicitly states that `PLAY_THROUGH` is a `PlannerDecision.decision_type`, not an `observed_class`.
12. `C4`/`C5` are never described as unconditionally `APPLICABLE`, and the benchmark contract's `UNKNOWN_NOT_MACHINE_CONFIRMED` status is present and is never described as being converted to a zero-event count.
13. The `C4`/`C5` machine-confirmation coverage-reporting requirement (`C4_confirmable_pairs / SIMPLE_CROSSFADE_pairs`, `C5_confirmable_pairs / SIMPLE_CROSSFADE_pairs`) is present verbatim.
14. A pure-Python re-implementation of the §12 algorithm, run against synthetic IDs, independently reproduces: order-invariance under input-list permutation; run-to-run determinism; zero reverse duplicates; no track appearing more than twice; an exact 22/28 holdout/dev split; an exact 9/21 `NG2` holdout/dev split; an exact 7/16 `NG4` holdout/dev split. No private corpus is read for this check.

This verifier does not decode audio, does not import any analyzer/ML library, and makes no network call. It exists because this contract makes numerous exact-number and exact-mechanism claims (§§8/12/14, and the benchmark contract's §16) that are cheap to check mechanically and easy to silently drift on a future edit; it is not added merely for ceremony.

## 17. Files

Modified by the original pass, and again by this repair:

- `docs/PROJECT_CHARTER.md` (repair: R3 wording fix only, §7/§Architecture-Boundaries/§P1-phase `PLAY_THROUGH` conflation removed)
- `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` (repair: `NG2`/`NG4`/`NG6`/`NG7` sections repaired per R1/R3/R4; §1–§15 still untouched)
- `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md` (this document; repair: R0/R2/R3 material added/rewritten)
- `tools/p0m4/verify_rescope_contract.py` (repair: R5 — new checks + deterministic selection self-tests)

Not modified, both passes: `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`, `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`, every file under `tools/p0m3/`, every other research document, `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §1–§15, and `main`. No internal contradiction was found that required touching the manifest schema or the pair catalog. If a future task finds this insufficient, it must stop and explain why rather than silently rewriting the historical broad catalog, per this task's own binding instruction.

## 18. PM review request

Please independently verify:

1. `git log --oneline -5` on `research/p0-feasibility` shows this repair commit directly on top of `0e2b1091479daa00aee74d3a2f6460278588b7c2`, and `git diff --stat` against that HEAD touches only the four files listed in §17.
2. `python tools/p0m4/verify_rescope_contract.py` reports all checks passing, including the 8 new R5 checks and the deterministic self-test.
3. `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §1–§15 are still byte-identical to the original pre-P0-M4-R1 version — `git diff` against `a4db362452ebe5a70c41c56943d512f70e57b316` shows changes confined to §16.
4. `docs/PROJECT_CHARTER.md`'s Architecture Boundaries §3–§5 still retain every original bullet (no deletions across either pass).
5. `NG2` (§16.5 of the benchmark contract) now names dimension 15 explicitly and states the exact aggregation formula.
6. §12 of this document contains the literal salt, hash rules, and exact split numbers, with no discretionary step remaining.
7. `PLAY_THROUGH` does not appear anywhere as a member of an "authorized rendered classes" list in either document.
8. `C4`/`C5` are `CONDITIONAL_WHERE_PREEXISTING_ACCEPTED_EVIDENCE_EXISTS` / `UNKNOWN_NOT_MACHINE_CONFIRMED`, not unconditionally `APPLICABLE`.
9. `main` is untouched: `git rev-parse main` still equals `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`.
10. After push, `git rev-parse HEAD` (local) equals `git rev-parse origin/research/p0-feasibility`.

---

P1 NOT STARTED. VALIDATION NOT RUN. HANDOFF TO PM.
