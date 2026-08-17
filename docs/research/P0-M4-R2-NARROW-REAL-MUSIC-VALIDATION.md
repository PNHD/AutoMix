# P0-M4-R2 — Narrow Real-Music Validation + Owner Listening Gate

Status date: 2026-08-18 (Phase 0 pass, repaired)

Binding task: GitHub Issue #9, "P0-M4-R2 — Narrow real-music validation + owner listening gate", executing the one bounded real-music validation authorized by the accepted P0-M4-R1 preservation-first rescope contract (`docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md`, accepted per Issue #8 comment `5317131442`).

## R0. Repair pass — binding PM review and scope

This document was repaired once, in the same session/branch, in response to PM review result `PHASE0_PF4_REPAIR_REQUIRED` (Issue #9 comment id `5318289406`), starting from the previously pushed HEAD `611acc586338abd1afbe8757ec54b1c4b6109e6d` (verified live before this repair — §2). This is **one narrow repair pass**, not a redesign: PF1/PF2/PF3/PF5 (and the manifest, candidate boundaries, split/subset membership, and comparator formulas they produced) are unchanged and provisionally accepted by the PM; only PF4's owner-facing annotation schema was defective and is repaired here.

**The defect (PM finding):** the prior owner annotation pack forced the owner to choose exactly one `assigned_class` per NG4 pair. Issue #9 PF4 requires the owner to label *allowed/appropriate narrow classes* using the existing P0-M2 `transition_class_policy` semantics (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §6), which explicitly permits more than one class to be simultaneously correct for one pair (e.g. an ordinary pair may legitimately allow both `NO_SPECIAL_TRANSITION` and `SIMPLE_CROSSFADE`). A single-choice UX silently narrowed a class-correctness gate into a preference gate.

**The repair:** the owner-facing schema now judges each of the three authorized narrow classes independently (true/false per class, never forced to a single winner) — §6 below. The existing 23-pair blind-token identity, the 46 source clips, and `blind_key.local.json` were **preserved unchanged** (patched in place via a new migration script, not regenerated). A new pure-function module maps a *completed* owner response onto the full `transition_class_policy` shape, mechanically rejecting the three narrow-scope forbidden classes independent of owner input — exercised in this pass only against synthetic rows, since no real owner response exists yet. The result remains `OWNER_NG4_GROUND_TRUTH_REQUIRED`; the owner has still not been asked to annotate anything.

## 0. Execution profile actually used

- **Execution surface:** Claude Desktop → Code, per `AGENTS.md`/`CLAUDE.md` execution-surface semantics.
- **Model:** `claude-sonnet-5`. **Reasoning effort:** High (Desktop UI selection).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Fallback:** NONE, not triggered.

## 1. Result

**`OWNER_NG4_GROUND_TRUTH_REQUIRED`** — an intermediate checkpoint, not a terminal product decision. Phase 0 preflight items PF1, PF2, PF3, PF5, and the reachable parts of PF6 are complete and independently machine-verified against the real 100-track opaque owner corpus. PF4 (non-circular NG4 expected-class ground truth) cannot be satisfied from any pre-existing accepted annotation, so this task built the required source-only owner annotation pack and stops here, per Issue #9's explicit instruction.

**No candidate/baseline comparison audio for owner listening was rendered.** The audio rendered in this pass is internal machine-evidence proof only (PF2/PF3 adapter proof, PF5 comparator proof, and the NG4 annotation pack's raw unprocessed clips) — none of it is a blinded preference/quality comparison pack, and none of it will be reused as such; Phase 1's actual candidate/baseline listening pack is not authorized until PF4 resolves.

## 2. Live-state verification (performed before any edit)

| Check | Value | Matches expectation? |
|---|---|---|
| Branch | `research/p0-feasibility` | yes |
| HEAD at original-pass session start | `0bf845066b2097a50549fdd8a984f5dafc550cca` | matches Issue #9's expected accepted starting HEAD exactly |
| HEAD at repair-pass session start | `611acc586338abd1afbe8757ec54b1c4b6109e6d` | matches this repair task's expected HEAD exactly (the original pass's own pushed commit) |
| `main` | `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` | untouched, unchanged (both passes) |

No intervening commits existed between either pass's expected HEAD and the live branch tip.

## 3. Read-first material actually read at current HEAD

`AGENTS.md`, `CLAUDE.md`, `.agents/skills/automix-task-contract/SKILL.md`, `.agents/skills/automix-forensic-research/SKILL.md`, `docs/PROJECT_CHARTER.md`, `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md` (referenced), `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md` (full, including §12), `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §5, §6, §16 (NG1–NG8), `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` (referenced via code), `docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` §6/§8 (for PF5's clean-room formulas), `tools/p0m4/verify_rescope_contract.py`, Issue #8 comments `5316347548` and `5317131442` (both fetched and read in full via `gh api`), and the accepted R2/R3 code: `tools/p0m3/transition_policy/policy/{contract,boundary,eligibility,metrics}.py`, `tools/p0m3/audio_render_shootout/dsp/{render_m1,render_common,mixing}.py`, `tools/p0m3/audio_render_shootout/scripts/{select_real_music_pairs,real_music_pipeline}.py`.

## 4. Phase 0 status — PF1 through PF6

| Item | Status | Evidence |
|---|---|---|
| **PF1** — deterministic 50-pair manifest | **PASS** | `tools/p0m4/narrow_validation/selection.py` implements the exact §12 algorithm (fixed salt `P0-M4-R1-NARROW-VALIDATION-v1`, SHA-256 pair-rank/split/subset keys). Run against the real 100-opaque-ID corpus (`id_map.local.json` keys only — never values/paths): exactly 50 pairs, 28 dev / 22 holdout, NG2 = 21 dev + 9 holdout = 30, NG4 = 16 dev + 7 holdout = 23. Deterministic on rerun (byte-identical). Frozen in `tools/p0m4/narrow_validation/manifest_sanitized.json`. 26/26 verifier checks pass (`verify_selection.py`, includes a synthetic self-test plus a cross-check that the committed manifest reproduces exactly from the current private corpus). |
| **PF2** — real-audio adapter proof | **PASS** | `tools/p0m4/narrow_validation/render_adapter.py` reuses, unmodified: `select_real_music_pairs.build_pair_compat_input`/`build_manifest_pair`, `real_music_pipeline.build_tx_fixture`/`convert_to_canonical_wav`, `policy.boundary.plan_transition_boundary`, `dsp.render_common.compute_segments`, `dsp.mixing.assemble_transition_render`/`apply_headroom_and_safety` — always called with `use_equal_power=True, use_bass_handoff=False, curve="equal_power"` (`dsp/render_m1.py`'s own "do less" call), regardless of what the planner's `allowed_transition_class_set` would additionally permit. No tempo/pitch/EQ engine is ever invoked. Run in `--render-audio` mode (actual ffmpeg decode + DSP mix, not just planning) against all 50 real frozen pairs: **50/50 succeeded, 0 failures, 0 forbidden-class hits.** 78/78 verifier checks pass (`verify_pf2_pf3.py`). |
| **PF3** — candidate-boundary provenance | **PASS** | Every candidate boundary is sourced exclusively from `corpus_analysis.local.json`'s already-cached Stage-B fields (`exit_candidate_t_ms`, `exit_structure_confidence`, `exit_structure_evidence_method`) — the same fields `select_real_music_pairs.py` already used for the accepted V1/V2/V3 manifest. No analyzer is invoked by this task. Of the 50 pairs, exactly **3** had cached evidence at `MEDIUM`/`HIGH` confidence (`BAR_SYNCHRONOUS_NOVELTY_PEAK` ×1, `INSTRUMENTAL_TAIL_DETECTED` ×2) and rendered `SIMPLE_CROSSFADE`; the other **47** had no sufficient cached evidence and the accepted eligibility guard (`policy/eligibility.py` Guard 2) correctly failed them closed to `NO_SPECIAL_TRANSITION` — no second, redundant gate was added by this task. |
| **PF4** — NG4 non-circular ground truth | **`OWNER_NG4_GROUND_TRUTH_REQUIRED`** (schema repaired) | Repository-wide search (every one of the 23 NG4-subset opaque-ID pair combinations) found no pre-existing MANUAL/authored "expected transition class" annotation for any of them — the one incidental hit (`RM042->RM002` inside `P0-M3-R3-ANALYZER-EVIDENCE-RECOVERY.md`) is an analyzer-evidence-lane cross-seed stability record, not an independent human class judgment, and using it would be circular regardless. Per Issue #9 PF4, this task built the required source-only owner annotation pack instead (§6 below). **PM repair (R0):** the owner response schema was corrected from a forced single `assigned_class` to independent per-class `class_acceptability` booleans, matching P0-M2's `transition_class_policy` semantics; the existing 23-token identity/clips/blind key were preserved unchanged. Still stops at this checkpoint — the owner has not yet annotated. |
| **PF5** — NG2 comparator executability | **PASS** | No accepted evidence anywhere confirms actual SimpMusic is locally Tier-1-runnable (`P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` only forensically analyzed the pinned source tree; it was never built/played back) — so this task used the already-authorized clean-room `SIMPMUSIC_CLASS_REFERENCE` path (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §6.3's own anticipated fallback). `tools/p0m4/narrow_validation/simpmusic_class_reference.py` re-implements only the public, `REIMPLEMENT_CLEAN_ROOM`-classified arithmetic P0-M1 §6 already cited (equal-power curve, Auto-duration BPM/key-gap formula, standard public Camelot-wheel distance) — 21/21 synthetic unit checks pass. Run against the real 30-pair NG2 subset (`ng2_comparator_proof.py`, same DSP path, zero new DSP): **30/30 succeeded (9/9 holdout, 21/21 dev), 0 `NG2_EXCLUDED_UNRENDERABLE` backfills needed.** 158/158 verifier checks pass (`verify_pf5.py`). |
| **PF6** — freeze before blinded listening | **PARTIAL (as far as reachable)** | Manifest/split/subset membership (PF1) and candidate boundaries (PF2/PF3) are frozen and committed. NG4 policy **cannot** be frozen yet — that is precisely PF4's open item. No dev/holdout label or opaque-ID mapping is exposed in any owner-facing artifact (the NG4 annotation pack's blind tokens carry no split/identity information). Blinded owner listening (Phase 3) has **not** begun. |

## 5. Frozen pair/split/subset counts

- Input corpus: **100** opaque track IDs (keys only; never printed/committed with their real-path values).
- Selected pairs: **50** (exactly the target; no shortfall).
- Split: **28 dev / 22 holdout**.
- NG2 subset: **30** = 21 dev + 9 holdout.
- NG4 subset: **23** = 16 dev + 7 holdout.
- Distinct opaque tracks used across the 50 pairs: **70** (no track exceeds 2 appearances; no reverse-duplicate pair).

## 6. NG4 owner annotation pack (PF4 checkpoint) — corrected schema

`tools/p0m4/narrow_validation/build_ng4_annotation_pack.py` (tracked, contains no real data) builds a **local-only** (gitignored) source-only annotation pack for exactly the 23 frozen NG4 pairs:

- For each pair: the raw, unprocessed last ~20s of the outgoing track and the raw, unprocessed first ~20s of the incoming track — no crossfade, no candidate/baseline identity, no dev/holdout label. The trim window is a fixed, deterministic 20s — never analyzer-chosen — so this stage cannot leak a "smart" boundary back into the owner's label.
- Pairs are assigned a random blind token (`NG4-01`..`NG4-23`, shuffled independently of the SS12 selection order/salt) so clip filenames and the response template never carry opaque IDs or split membership.
- Outputs: `clips/` (46 WAV files, two per pair), `blind_key.local.json` (token → opaque IDs/split — **local-only, never committed**), `response_template.json`, `INSTRUCTIONS.md`.

**Corrected response schema (R0 repair):** each row is now `{"token": "NG4-07", "class_acceptability": {"NO_SPECIAL_TRANSITION": null, "GAPLESS": null, "SIMPLE_CROSSFADE": null}, "confidence": null, "note": ""}` — the owner sets each of the three booleans independently; any combination of zero, one, two, or three `true` values is valid. The old single-scalar `assigned_class` field no longer exists anywhere in the schema. `FULL_DJ_BLEND`/`SHORT_EQ_BLEND`/`CUT` are never offered as owner choices — they are narrow-scope forbidden classes, added to the eventual policy mechanically (§6.1 below), never an owner annotation question.

The corrected `INSTRUCTIONS.md` explicitly states more than one class can be true, gives the worked "ordinary pair" and "continuous work" examples from the PM review, and clarifies the owner is judging transition *style acceptability in the abstract* (assuming competent execution), never a specific candidate implementation's audio quality (that happens later, in blinded listening).

The previously-unused `--seed-file` CLI option was removed from `build_ng4_annotation_pack.py` (it advertised a capability the code never implemented).

### 6.1 Policy materialization (not yet exercised against real data)

`tools/p0m4/narrow_validation/ng4_policy_materialization.py` maps a **completed** owner response row onto the full P0-M2 `transition_class_policy` shape:

- every class the owner marked `true` → `accepted_unconditional`;
- a class marked `false` or left unanswered is **not** added to any explicit list — it falls through to the schema's own closed-world rejection default (SS6.1 rule 2), never treated as machine-confirmed-unsafe;
- the three forbidden classes (`FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, `CUT`) are added to `rejected` **mechanically**, with a mandatory reason citing the narrow-scope contract restriction — independent of any owner input;
- `accepted_conditional`/`rejected_conditional` are always empty — this source-only stage never invents conditional machine evidence;
- mutual exclusivity (SS6.1 rule 1) is defensively re-verified on every call.

This module is exercised in this pass **only** against synthetic response rows (`verify_pf4_pack.py`) — no real owner response exists yet, and it is not invoked against real data until a future session after the owner completes `response_template.json`.

### 6.2 In-place schema migration (existing pack preserved)

`tools/p0m4/narrow_validation/patch_ng4_pack_schema.py` was used, in this session, to migrate the *already-built* local pack (built in the original P0-M4-R2 pass) from the old single-`assigned_class` schema to the corrected `class_acceptability` schema **without regenerating `clips/` or `blind_key.local.json`**. It refuses to run if the existing template already contains owner answers (protects real data from being discarded) or if the token count/set does not match. Verified after migration: same 23 tokens, same 46 clip files, only `INSTRUCTIONS.md`/`response_template.json` rewritten.

The pack was originally built in the prior session (23/23 pairs, 46/46 clips) and its schema was repaired in place in this session — no audio was regenerated.

## 7. Privacy audit

- Every tracked JSON/py file this task added was scanned for path-like strings (`/`, `\`, drive-letter patterns) and non-opaque-length tokens; zero hits (`verify_selection.py`, `verify_pf2_pf3.py`, `verify_pf5.py`, `verify_pf4_pack.py`).
- `verify_pf4_pack.py`'s local-pack layer reads `blind_key.local.json` **token keys only** (never values) to confirm identity preservation; it never prints or logs an opaque ID, a split label, or a path.
- Only opaque `RM###` IDs and plain numbers appear in any tracked evidence file.
- `id_map.local.json`, `corpus_analysis.local.json`, and this task's own `work_local/` tree (decoded/rendered audio, the NG4 pack, the blind key) are read/written locally only and are already gitignored (pre-existing repo pattern for the first two; a new `tools/p0m4/narrow_validation/.gitignore` for the third).
- No filenames, titles, artists, albums, or audio hashes appear anywhere in tracked output.

## 8. Verifier / validation commands and results

```
python tools/p0m4/verify_rescope_contract.py                       # pre-existing, unmodified — still 42/42 PASS (not re-touched by this task)
python tools/p0m4/narrow_validation/verify_selection.py            # 26/26 PASS
python tools/p0m4/narrow_validation/render_adapter.py --work-dir ... --evidence-out ... --render-audio   # 50/50 SUCCESS, 0 forbidden-class hits
python tools/p0m4/narrow_validation/verify_pf2_pf3.py               # 78/78 PASS
python tools/p0m4/narrow_validation/verify_simpmusic_class_reference.py  # 21/21 PASS
python tools/p0m4/narrow_validation/ng2_comparator_proof.py --work-dir ... --evidence-out ...  # 30/30 SUCCESS
python tools/p0m4/narrow_validation/verify_pf5.py                   # 158/158 PASS
python tools/p0m4/narrow_validation/build_ng4_annotation_pack.py --pack-dir ...  # 23/23 pairs, pack built (original pass)
python tools/p0m4/narrow_validation/patch_ng4_pack_schema.py --pack-dir ...      # RESULT: PATCHED, 23 tokens preserved, clips/blind_key untouched (repair pass)
python tools/p0m4/narrow_validation/verify_pf4_pack.py               # 89/89 PASS (schema-shape + materialization unit tests + local-pack identity checks; repair pass)
```

## 9. Tracked deliverables (this task)

- `tools/p0m4/narrow_validation/selection.py` — PF1 deterministic §12 selection algorithm.
- `tools/p0m4/narrow_validation/verify_selection.py` — PF1 verifier.
- `tools/p0m4/narrow_validation/manifest_sanitized.json` — the frozen 50-pair manifest (opaque IDs only).
- `tools/p0m4/narrow_validation/render_adapter.py` — PF2/PF3 real-audio adapter + evidence generator.
- `tools/p0m4/narrow_validation/verify_pf2_pf3.py` — PF2/PF3 verifier.
- `tools/p0m4/narrow_validation/boundary_evidence_plan_only_sanitized.json`, `boundary_evidence_render_sanitized.json` — sanitized PF2/PF3 evidence (opaque IDs + numbers only).
- `tools/p0m4/narrow_validation/simpmusic_class_reference.py` — PF5 clean-room comparator formulas.
- `tools/p0m4/narrow_validation/verify_simpmusic_class_reference.py` — PF5 formula unit tests (synthetic).
- `tools/p0m4/narrow_validation/ng2_comparator_proof.py` — PF5 real-corpus executability proof.
- `tools/p0m4/narrow_validation/verify_pf5.py` — PF5 evidence verifier.
- `tools/p0m4/narrow_validation/ng2_comparator_evidence_sanitized.json` — sanitized PF5 evidence.
- `tools/p0m4/narrow_validation/build_ng4_annotation_pack.py` — PF4 owner annotation pack builder (no real data embedded); **repaired** this pass to the independent per-class `class_acceptability` schema.
- `tools/p0m4/narrow_validation/patch_ng4_pack_schema.py` — **new this pass.** In-place migration of an existing local pack to the corrected schema, preserving clips/blind-key identity.
- `tools/p0m4/narrow_validation/ng4_policy_materialization.py` — **new this pass.** Pure function mapping a completed owner response to the P0-M2 `transition_class_policy` shape; mechanically rejects the narrow-scope forbidden classes.
- `tools/p0m4/narrow_validation/verify_pf4_pack.py` — **new this pass.** PF4 schema/pack verifier (89 checks: schema shape, materialization unit tests against synthetic rows, local-pack identity/privacy).
- `tools/p0m4/narrow_validation/.gitignore` — private/local-only artifact exclusion for this task's own working directory.
- This report.

## 10. Local-only artifacts (never committed)

- `tools/p0m4/narrow_validation/work_local/decoded/` — decoded canonical WAVs (PF2 proof).
- `tools/p0m4/narrow_validation/work_local/renders/` — rendered SIMPLE_CROSSFADE/NO_SPECIAL_TRANSITION proof audio (PF2 proof).
- `tools/p0m4/narrow_validation/work_local/ng2_comparator_renders/` — rendered comparator audio (PF5 proof).
- `tools/p0m4/narrow_validation/work_local/ng4_annotation_pack/` — the NG4 owner annotation pack (clips, blind key, response template, instructions).

## 11. What must happen next

1. **Owner checkpoint (this task's stop point):** the project owner listens to the 23-pair NG4 annotation pack (`tools/p0m4/narrow_validation/work_local/ng4_annotation_pack/`, per its `INSTRUCTIONS.md`) and fills in `response_template.json`.
2. A future session continues the **same** narrow-validation task from this frozen manifest/evidence (per Issue #9 Phase 4: "do not regenerate audio unless PM finds a deterministic defect"), builds the frozen `transition_class_policy` from the owner's non-circular labels, completes the remaining PF6 freeze, proceeds to Phase 1 render / Phase 2 machine evidence / Phase 3 blinded listening pack construction, and stops again at `OWNER_NARROW_LISTENING_REQUIRED`.
3. `NARROW_P1_ENTRY_ALLOWED` or `STOP_OR_REDESIGN` cannot be claimed until valid blinded owner ratings are returned and NG1–NG8 are all evaluated. **P1 has not started and must not start.**

---

P1 NOT STARTED. NG1–NG8 NOT EVALUATED. CANDIDATE/BASELINE LISTENING NOT RENDERED. HANDOFF TO PM.
