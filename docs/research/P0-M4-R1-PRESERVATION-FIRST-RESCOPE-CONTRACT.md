# P0-M4-R1 — Preservation-First Rescope Contract

Status date: 2026-08-17

Binding task: PM-authorized "P0-M4-R1 — PRESERVATION-FIRST RESCOPE CONTRACT" specification-bridge task, following the accepted P0-M4 decision `RESCOPE_BEFORE_P1` (`docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md`).

Accepted starting HEAD: `a4db362452ebe5a70c41c56943d512f70e57b316` (verified before any edit — see §1).

## 0. Execution profile actually used

- **Execution surface:** Claude Desktop → Code (per `AGENTS.md`/`CLAUDE.md` execution-surface semantics — the embedded runtime self-identifies as a Claude Code runtime, which is explicitly not a stop condition for this surface).
- **Model:** `claude-sonnet-5`. **Reasoning effort:** High (Desktop UI selection, not independently introspectable, per the same non-stop-condition rule used throughout this project's prior accepted reports).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Agent teams:** OFF. **Nested agents:** OFF. **Parallel delegation:** OFF. **Fallback:** NONE, not triggered.
- **Session:** new session, as required.

## 1. Result

**`RESCOPE_CONTRACT_READY_FOR_PM_REVIEW`**

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

**`PRESERVATION_FIRST_LOCAL_AUTOMIX`**, as recorded in `docs/PROJECT_CHARTER.md`'s "Post-P0 scope decision (P0-M4)" section (added by this task): local/DRM-free audio only, preservation-first, consumer listening (not DJ/highlight playback), simple/no-special transition first, fail-closed. Default-enabled classes: `PLAY_THROUGH`/`NO_SPECIAL_TRANSITION`, `GAPLESS` only at genuine natural/continuous-work boundaries, `SIMPLE_CROSSFADE` at a preservation-safe near-end boundary (§7 below).

### 5.2 What is explicitly excluded?

`FULL_DJ_BLEND`, tempo/time-stretch automation, pitch/key shifting, beat/downbeat-synchronized overlap as a product promise, automatic song-shortening/highlight playback, automatic non-natural `CUT` as default behavior. `SHORT_EQ_BLEND` is research-only, off by default, and does not become a production default merely because research code for it already exists (`docs/PROJECT_CHARTER.md`, `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md` §13).

### 5.3 What must be validated before P1 may begin?

Two independent conditions, both required:

1. This Charter/benchmark revision (this task's diff) is accepted by the PM.
2. The one bounded real-music preservation-first validation defined in §7–§13 below independently passes every applicable `NG1`–`NG8` threshold (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16), including every holdout component, and terminates with `NARROW_P1_ENTRY_ALLOWED` (§13).

### 5.4 Which old P0-M2 gates remain binding?

`G1`–`G8` (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §12) remain fully intact, unmodified, and binding as the historical gate for the original broad, `FULL_DJ`-capable P1 hypothesis. No numeric value in `G1`–`G8` was changed by this task (verified, §14 item 7).

### 5.5 Which broad/FULL_DJ-specific gates are not applicable to the narrow scope?

`G3` (beat/downbeat/cue/phrase production requirement) is `REPLACED_FOR_NARROW_SCOPE` by `NG3` (preservation/boundary safety). Within the catastrophic-failure taxonomy, `C1_BEAT_TRAINWRECK`, `C2_BAR_PHASE_ERROR`, `C3_WRONG_PHRASE_LOCATION`, `C7_STRETCH_ARTIFACT`, `C8_PITCH_ARTIFACT`, and `C10_WRONG_METADATA_POISONING` are `NOT_APPLICABLE` to the narrow scope (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16.9's full mapping table).

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

**Default-enabled:**

| Class | Definition source | Product claim |
|---|---|---|
| `PLAY_THROUGH` / `NO_SPECIAL_TRANSITION` | `tools/p0m3/transition_policy/policy/contract.py::build_fallback_decision()`; `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1 | Zero overlap; no processing. First-class result, not an error state. |
| `GAPLESS` | Only when `is_continuous_work = true` (a genuine natural/continuous-work boundary) — `tools/p0m3/transition_policy/policy/eligibility.py`, `policy/boundary.py` | Zero overlap, sample-contiguous join. |
| `SIMPLE_CROSSFADE` | Volume/gain overlap only, at a preservation-safe near-end boundary selected by the R2 planner | Equal-power crossfade, no beat/downbeat/tempo/pitch claim. |

**Excluded from the first production prototype:** `FULL_DJ_BLEND`, tempo/time-stretch automation, pitch/key shifting, beat/downbeat-synchronized overlap as a product promise, automatic highlight/song-shortening mode, automatic non-natural `CUT` as a default behavior.

**Research-only, off by default:** `SHORT_EQ_BLEND` — may remain in the research harness (`dsp/mixing.py`'s bass-handoff/EQ-adjacent machinery) but must not become a product default until a same-boundary real-listening result proves it improves over `SIMPLE_CROSSFADE` without introducing loudness holes or fatigue, per a separate, explicit, future PM-approved gate.

## 8. NG1–NG8 narrow gate (pointer + summary)

Full binding definitions are in `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16. Summary:

| Gate | One-line requirement |
|---|---|
| `NG1` | Blind preference vs. fixed equal-power crossfade: tie ≤20%; combined n≥40 decisive, win rate ≥65%, p<0.05; holdout n≥18 decisive, win rate ≥60%. |
| `NG2` | SimpMusic-class comparison, 30 pairs (21/9): mean preference ≥ SimpMusic-class +0.5. |
| `NG3` | `outgoing_content_preservation_ratio ≥0.95` every transition; 100% on holdout; `<0.90` is catastrophic and independently blocks entry. |
| `NG4` | Only `PLAY_THROUGH`/`NO_SPECIAL_TRANSITION`/`GAPLESS`/`SIMPLE_CROSSFADE` ever rendered; 23-pair subset (7 holdout); class-match ≥80% overall, ≥6/7 holdout; forbidden-class rate 0/50, 0/22 holdout. |
| `NG5` | Holdout frozen before listening/tuning; no pair-specific tuning; independent pass on every gate's own holdout component. |
| `NG6` | ≤1/50 confirmed catastrophic pair overall; 0/22 holdout; narrowed `C1`–`C11` applicability (§5.5 above). |
| `NG7` | ≤1/50 `HUMAN_VETO` overall; 0/22 holdout; compact A/B/Tie + separate veto/reason UX. |
| `NG8` | Reproduction checklist executed once; pinned engine + frozen manifest reproduces identical objective metrics (or documented tolerance). |

## 9. Existing R3 renderer binding (read-only inspection; nothing invoked or modified)

Every class the narrow scope authorizes already has a reusable, already-existing code path. No new DSP is required, so `BLOCKED_EXISTING_RENDERER_GAP` does not apply.

### 9.1 `SIMPLE_CROSSFADE`

- **Renderer entry point:** [`tools/p0m3/audio_render_shootout/dsp/render_m1.py`](../../tools/p0m3/audio_render_shootout/dsp/render_m1.py)`::render()` — documented in-file as "M1 -- planner-correct equal-power SIMPLE_CROSSFADE reference"; emits `rendered_transition_class: "SIMPLE_CROSSFADE"`, `gain_law: "equal_power"`, `beat_alignment_applied: false`, `applied_tempo_ratio: 1.0`, and deliberately never applies tempo correction or beat alignment even when the planner also permits a more complex class — exactly the "do less" reference this scope needs.
- **Shared DSP it calls:** [`dsp/mixing.py`](../../tools/p0m3/audio_render_shootout/dsp/mixing.py)`::assemble_transition_render(..., use_equal_power=True, use_bass_handoff=False)`, which calls `mix_overlap(curve="equal_power")` → `equal_power_gains()` (constant-power crossfade, public-domain formula, no GPL/Signalsmith code involved) and `apply_headroom_and_safety()` for deterministic clip prevention.
- **Boundary/segment logic it consumes:** [`dsp/render_common.py`](../../tools/p0m3/audio_render_shootout/dsp/render_common.py)`::load_scenario_context()` / `compute_segments()`, which reads the R2 planner's `PlannerDecision` onset/content-end/entry timestamps verbatim (never re-derived or guessed).

### 9.2 `PLAY_THROUGH` / `NO_SPECIAL_TRANSITION` / `GAPLESS`

These three classes are defined as **zero overlap** by construction (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5.1: "None" automation). No dedicated audio-mixing DSP is needed or exists for them, and none is missing:

- **Decision layer:** [`tools/p0m3/transition_policy/policy/contract.py`](../../tools/p0m3/transition_policy/policy/contract.py)`::build_fallback_decision()` already produces `decision_type ∈ {"PLAY_THROUGH", "NO_SPECIAL_TRANSITION"}` with the correct `allowed_transition_class_set` (`[]` for `PLAY_THROUGH`, `["NO_SPECIAL_TRANSITION"]` otherwise) — first-class results, not error states (see the `AC10` comment at `contract.py` line 47).
- **Eligibility/selection layer:** [`policy/eligibility.py`](../../tools/p0m3/transition_policy/policy/eligibility.py) lines 134/210 and [`policy/boundary.py`](../../tools/p0m3/transition_policy/policy/boundary.py) lines 134/278 already select `GAPLESS`/`NO_SPECIAL_TRANSITION` when no safe near-end candidate exists or when the pair is annotated `is_continuous_work`/`sequencing_suppression_intended`.
- **Rendering, mechanically:** with `overlap_len_smp == 0`, the exact same `dsp/render_common.py::compute_segments()` segment-assembly logic used by `SIMPLE_CROSSFADE` already produces `[outgoing_pre] + [] + [incoming_post]` — i.e. plain concatenation with zero or natural gap. This is a direct, zero-new-code restriction of the existing segment-assembly path, not a missing interface.

**Conclusion:** every one of the three authorized classes is renderable using already-existing, already-accepted code. The next validation task must reuse `render_m1.render()` (or the underlying `dsp.mixing`/`dsp.render_common` functions it calls) for `SIMPLE_CROSSFADE`, and plain segment concatenation (zero overlap) for the other two — no new DSP, no new renderer file, no analyzer.

## 10. Loudness / safety contract

Carried forward unchanged from the accepted P0-M2 objective definitions (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §8/§10):

- Momentary = 400 ms, short-term = 3 s, ITU-R BS.1770-5 terminology (EBU R128/Tech 3341 window naming).
- `COND_LOUDNESS_OK`: momentary loudness delta ≤2 LU, unchanged.
- `C6_GROSS_LOUDNESS_DISCONTINUITY`: >6 LU momentary jump between consecutive 100 ms-stepped measurements, or >3 LU momentary step at a `CUT`/`GAPLESS` splice — unchanged, still safety-critical, still `APPLICABLE` under the narrow scope (§5.5/`NG6` mapping).

These metrics remain **objective diagnostics** and **catastrophic-failure evidence** (`C6` firing) and **explanatory evidence** for a blind preference/veto outcome. They are never, by themselves, sufficient to authorize P1 — `NG1`'s blind human preference result remains the final proof of actual audible benefit. No new arbitrary loudness threshold was invented to make any gate pass more easily.

## 11. Provider / legal boundary

The narrow validation and the first authorized P1 are **local / DRM-free audio only**. Provider integration (Spotify, Apple Music, YouTube Music, or any other streaming provider) remains **deferred** — it is not part of this scope and is not unlocked by this contract.

Explicitly forbidden, unconditionally: DRM circumvention, protected-stream extraction, cookie/token/session extraction, undocumented provider endpoints, MITM, process injection, memory hooking. Ordinary public Spotify/Apple APIs do not provide the PCM/control surface this engine needs, and no claim to the contrary is made anywhere in this document or the Charter changes.

## 12. Pair selection / anti-cherry-picking rule

The validation uses real local/DRM-free music only, from the existing authorized owner corpus already used by prior R3 tasks (`owner_music_input`, unchanged root, not re-scanned or broadened).

**Frozen selection rule (must be applied before any rendering or listening begins, and never revisited afterward):**

1. Enumerate the full ordered-pair universe from the existing corpus (as R3's replay already does — `tools/p0m3/audio_render_shootout/scripts/final_real_corpus_replay.py`'s candidate-universe construction, reused, not reimplemented).
2. Stratify candidates using only **deterministic, non-proprietary, already-available** signals present in the existing cached corpus analysis (`real_music/work_local/corpus/corpus_analysis.local.json`) — specifically: duration bins, integrated-loudness-difference bins, measurable leading/trailing silence characteristics, and simple level/energy characteristics already computed by the existing harness (e.g. the bounded spectral/energy proxies used elsewhere in R3, not a new analyzer).
3. Assign each candidate pair to `dev`/`holdout` via a fixed, pre-registered pseudorandom split (seeded once, recorded in the run manifest, never reseeded after any result is seen), targeting the `NG` corpus minimums (§8): 50 total (28 `dev` / 22 `holdout`), with the `NG4` 23-pair/7-holdout fallback-policy subset and the `NG2` 30-pair/9-holdout SimpMusic-class subset drawn from within that same frozen 50-pair pool where their case requirements are met, per the same subset-not-additive convention already used by the broad Tier-1 corpus (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §2 `note`).
4. Freeze the full pair list, `pair_id`s, and `dev`/`holdout` assignment in a committed-or-sanitized manifest before any render or listening session starts.

**Explicitly not used for selection:** filenames, artist/title identity, any web search of track identities, genre oracle, harmonic oracle, downbeat model, phrase model, structure model, CUE-DETR, or All-In-One. No new analyzer is authorized merely to select friendly validation pairs.

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

`tools/p0m4/verify_rescope_contract.py` (new, docs-only checks, no audio/network/model dependency) independently checks:

1. `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` still contains the original, unmodified `G1`–`G8` numeric anchors (`74`, `52`, `22`, `65%`, `60%`, `30`, `21`, `9`).
2. The new §16 appendix contains all eight `NG1`–`NG8` headings and the `50`/`28`/`22` corpus arithmetic.
3. The tie-rate arithmetic (`50 - floor(0.20*50) = 40`, `22 - floor(0.20*22) = 18`) is present verbatim.
4. `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md` contains the exact forbidden-class list and the `SHORT_EQ_BLEND`/research-only/off-by-default statement.
5. `docs/PROJECT_CHARTER.md` contains `PRESERVATION_FIRST_LOCAL_AUTOMIX` as the authorized first production scope and explicitly states the broad engine does not inherit authorization from it.
6. None of the tracked `docs/**/*.md` files contain the unqualified prohibited-claim strings listed in §15.

This verifier does not decode audio, does not import any analyzer/ML library, and makes no network call. It exists because this task made numerous exact-number claims (§§8/12/14) that are cheap to check mechanically and easy to silently drift on a future edit; it is not added merely for ceremony.

## 17. Files

Modified:

- `docs/PROJECT_CHARTER.md`
- `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`

Created:

- `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md` (this document)
- `tools/p0m4/verify_rescope_contract.py`

Not modified: `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`, `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`, every file under `tools/p0m3/`, every other research document. No internal contradiction was found that required touching the manifest schema or the pair catalog; the narrow-validation manifest/corpus shape is fully specified in prose in §8/§12 above and in `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §16, which is sufficient for a future validation task to implement without a schema change. If a future task finds this insufficient, it must stop and explain why rather than silently rewriting the historical broad catalog, per this task's own binding instruction.

## 18. PM review request

Please independently verify:

1. `git log --oneline -3` on `research/p0-feasibility` shows this task's commit directly on top of `a4db362452ebe5a70c41c56943d512f70e57b316`, and `git diff --stat` against that HEAD touches only the four files listed in §17.
2. `python tools/p0m4/verify_rescope_contract.py` reports all checks passing.
3. `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §1–§15 are byte-identical to the pre-task version (only §16 was appended) — `git diff` shows an addition-only diff at the end of the file.
4. `docs/PROJECT_CHARTER.md`'s Architecture Boundaries §3–§5 retain every original bullet (no deletions), with only annotations added.
5. `main` is untouched: `git rev-parse main` still equals `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`.
6. After push, `git rev-parse HEAD` (local) equals `git rev-parse origin/research/p0-feasibility`.

---

P1 NOT STARTED. VALIDATION NOT RUN. HANDOFF TO PM.
