# P0-M3-R3 — Final real-corpus replay

Status date: 2026-08-17

Binding task: Issue #7 PM comment "PM REVIEW — ALIGNMENT-ANCHOR CONTRACT
ACCEPTED; ONE PRE-FLIGHT CONSISTENCY FIX FOLDED INTO FINAL REAL-CORPUS
REPLAY" (comment id `5313303841`).

Starting HEAD: `8154227b28515e021d46e008b4658d993abfffe7` (verified before
any edit).

This is the **final planned engineering task of P0-M3-R3**. Per the task's
explicit finish cap, this document closes with one of `REAL_RENDER_CANDIDATE_RECOVERED`,
`R3_FINAL_PARTIAL_NO_VALID_V1_V2`, `BLOCKED`, or `FAIL`, and no further
analyzer/oracle/calibration task is opened from this result.

## Result

**`R3_FINAL_PARTIAL_NO_VALID_V1_V2`**

Zero strict FULL_DJ survivors in either V1 (close-tempo, ≤2% stretch) or V2
(conditional-tempo, 3–6% stretch) after replaying the complete cached
100-track corpus through the unchanged canonical evaluator. This is an
honest, accepted negative/PARTIAL feasibility outcome, not a bug.

---

## Two separate things this document does NOT let readers conflate

### 1. CONTRACT REPRESENTATION FIX (this task, code-level, generic)

A narrow defect in `tools/p0m3/transition_policy/policy/contract.py`'s
`build_boundary_transition_decision()`: `beat_phase_relation` /
`beat_alignment_action` and `bar_phase_relation` / `bar_alignment_action`
were BOTH derived from a single `both_beat_targets_known` flag. Under the
newly-accepted alignment-anchor contract separation (previous task,
`P0-M3-R3-ALIGNMENT-ANCHOR-CONTRACT.md`), beat and downbeat presence can now
differ (PARTIAL EXPLICIT mode), so a boundary with a known beat target but a
**missing** downbeat target could still incorrectly emit a downbeat/bar
alignment action.

Repaired to two independent flags, `both_beat_targets_known` /
`both_downbeat_targets_known`, each additionally requiring the corresponding
side's incoming target not precede its own audible entry (invalid-before-entry
safety, unchanged semantics, now applied per-side instead of jointly). Raw
(possibly invalid) target values are never clamped or rewritten — only the
render-plan action/relation fields are withheld. See `policy/boundary.py`'s
new `incoming_beat_alignment_invalid` / `incoming_downbeat_alignment_invalid`
per-side flags (computed once, passed into the decision builder rather than
recomputed).

`select_real_music_pairs.py`'s new `alignment_anchor_fields()` helper
consumes the same separation generically at the selector layer: outgoing/
incoming candidates now carry INDEPENDENT `beat_alignment_target_ms` /
`downbeat_alignment_target_ms` (sourced from each side's own real per-track
beat/downbeat confidence, never fabricated, never keyed to any specific
opaque RM id) instead of one coupled `beat_downbeat_aligned` boolean.

**This fix is representation-only.** For any boundary where both beat AND
downbeat are independently HIGH-confidence on both sides — which is the
*only* case that ever authorized `FULL_DJ_BLEND` before this task —
`policy.boundary.plan_transition_boundary`'s `boundary_alignable` gate still
requires all four independent presence checks simultaneously, so the
resolved values and the FULL_DJ_BLEND outcome are **numerically identical**
to the prior coupled computation. Verified directly in this pass: the
replay's `canonical_planner_full_dj_withheld` rejection counter is `0` for
both V1 and V2 (see below) — no candidate ever reached the canonical
planner's alignment gate as the deciding factor at all, because earlier,
completely unrelated gates (see next section) already rejected every
tempo-eligible candidate first.

### 2. ANALYZER COMPATIBILITY EVIDENCE (measured this pass, not fixed by #1)

The replay's actual blocker is evidence scarcity in unrelated gates —
`analysis_confidence`, `genre`, `texture`, `structure`, `harmonic` — that the
alignment-anchor separation neither touches nor could touch. See "Dominant
remaining gates" below. **The new alignment-anchor field does not shortcut
or substitute for any of these; it was not the deciding gate for a single
candidate in this replay.**

---

## Pre-flight validation

```
python tools/p0m3/transition_policy/run_benchmark.py
python tools/p0m3/transition_policy/verify.py
```

**220/220 assertions PASS** (up from the prior accepted 179/179 — 41 new
mutation assertions added, all 179 prior assertions retained and re-verified
unchanged). New coverage:

1. beat present + downbeat missing → beat action may apply, bar action MUST
   be `NOT_APPLICABLE` (reuses the existing TX-08 PARTIAL EXPLICIT fixture).
2. downbeat present + beat missing → bar action may apply, beat action MUST
   be `NOT_APPLICABLE` (new symmetric fixture).
3. incoming beat target precedes entry → beat action MUST be
   `NOT_APPLICABLE`; bar action (independently valid) still applies.
4. incoming downbeat target precedes entry → bar action MUST be
   `NOT_APPLICABLE`; beat action (independently valid) still applies.
5. both invalid → both actions `NOT_APPLICABLE`.
6. raw invalid timestamps remain visible in diagnostic fields (never
   clamped/rewritten) — checked for every mutation 3/4/5 case.
7. TX-01..08 valid behavior unchanged — independently re-derived (not
   cached), winner + FULL_DJ_BLEND authorization re-checked per fixture,
   plus a structural proof that no TX-01..08 fixture has a beat/downbeat
   split (the repair is a provable no-op for every existing fixture).

`run_benchmark.py`'s `boundary_planning.json` shows TX-01..08 all
`matches_expectation: true`, unchanged from the prior accepted run.

## Corpus / replay scope

- Corpus: the existing authorized 100-track owner corpus at
  `owner_music_input` (unchanged root, not re-scanned).
- Evidence source: `real_music/work_local/corpus/corpus_analysis.local.json`
  + `id_map.local.json` (already cached from prior accepted sessions) only.
- **No audio was decoded.** No All-In-One, BeatNet, madmom, harmonic, or
  style-model pass was rerun, corpus-wide or otherwise. No render, no
  Signalsmith, no Rubber Band, no owner listening pack.
- Candidate-universe construction: reused verbatim from the accepted
  Stage-B selector (`select_real_music_pairs.py`'s `build_candidate` /
  `build_pair_compat_input` / `exit_candidate_renderable`) and its shared
  gate-classification module (`pair_gate_audit.py`'s `audit_universe` /
  `rank_near_misses`) — no gate/threshold/ranking logic was reimplemented.
- New: `scripts/final_real_corpus_replay.py` adds the one proof step pool
  membership alone never performed — invoking the REAL, unmodified
  `policy.boundary.plan_transition_boundary()` on every gate-passing
  candidate to honestly prove (or refuse) `FULL_DJ_BLEND`, via a synthetic
  transition fixture built directly from cached per-track analysis (never
  from a manifest, never from audio).

## V1 final result (close-tempo, ≤2% stretch)

| Metric | Count |
|---|---:|
| Total pair universe (100×99 ordered pairs) | 9,900 |
| Tempo-eligible universe | 620 |
| Strict FULL_DJ survivors | **0** |

Per-gate rejection counts (a pair can fail more than one gate; counts are
not mutually exclusive):

| Gate | Rejections / 620 |
|---|---:|
| `analysis_confidence` | 620 (100%) |
| `texture` | 589 |
| `genre` | 588 |
| `downbeat` | 576 |
| `structure` | 530 |
| `harmonic` | 469 |
| `vocal` | 316 |
| `beat` | 148 |
| `exit_structure_not_renderable` | 0 |
| `bass` | 0 |
| `tempo` | 0 |
| `canonical_planner_full_dj_withheld` (reached only after all hard gates + renderability already passed) | 0 |

## V2 final result (conditional-tempo, 3–6% stretch)

| Metric | Count |
|---|---:|
| Total pair universe (100×99 ordered pairs) | 9,900 |
| Tempo-eligible universe | 1,025 |
| Strict FULL_DJ survivors | **0** |

| Gate | Rejections / 1,025 |
|---|---:|
| `analysis_confidence` | 1,024 (99.9%) |
| `texture` | 974 |
| `genre` | 971 |
| `downbeat` | 953 |
| `structure` | 892 |
| `harmonic` | 798 |
| `vocal` | 544 |
| `beat` | 206 |
| `bass` | 2 |
| `exit_structure_not_renderable` | 0 |
| `tempo` | 0 |
| `canonical_planner_full_dj_withheld` | 0 |

## Survivors

**None.** `strict_full_dj_survivor_count == 0` for both V1 and V2. No
candidate was selected; nothing is queued for owner listening review.

## Dominant remaining gates

`analysis_confidence` is the near-universal blocker (100% of V1's
tempo-eligible pool, 99.9% of V2's) — it is the aggregate
`min(structure_strength, genre_strength, harmonic_strength)` and requires
`HIGH` on all three. `genre_strength` is `HIGH` only when BOTH sides have
non-empty locally-recovered genre tags; most of this corpus's tracks carry
no trustworthy embedded genre tag (`genre_tag_provenance: "UNKNOWN"` — see
prior accepted `P0-M3-R3-STAGE-B-EVIDENCE-AUDIT` findings), which alone caps
`analysis_confidence` below `HIGH` for the large majority of pairs
regardless of every other gate. `texture`, `structure`, and `harmonic`
UNKNOWN/incompatible evidence compound this independently. **Beat/downbeat
confidence — the gate this task's contract fix targeted — is comparatively
the least-restrictive gate in this corpus** (148/620 and 206/1025
rejections, the two lowest non-zero counts alongside `bass`), and
`canonical_planner_full_dj_withheld` is `0` in both categories: no candidate
ever reached the alignment-anchor gate as its deciding rejection, because it
was already rejected by earlier, unrelated gates first.

## Top near misses

Full top-10 lists (opaque RM ids only) are in
`results/final_real_corpus_replay_sanitized.json`. The single closest V2
near miss (3 failed gates: `harmonic` UNKNOWN, `texture` INCOMPATIBLE,
`analysis_confidence` UNKNOWN) has both beat AND downbeat independently
`COMPATIBLE` — its blockers are entirely unrelated to the alignment-anchor
contract this task repaired. No near miss in either list is blocked
primarily or solely by the alignment-anchor gate.

## Alignment-anchor evidence consumed

None beyond the generic, per-track real beat/downbeat confidence already
present in `corpus_analysis.local.json` for every candidate uniformly. The
accepted RM014 diagnostic
(`docs/research/P0-M3-R3-RM014-ENTRY-ANCHOR-FEASIBILITY.md`, result
`SEPARATE_ENTRY_AND_ALIGNMENT_ANCHOR_JUSTIFIED`) is architectural motivation
for the contract shape only — its specific candidate timestamps (7374 ms /
18650 ms) were diagnostic-only, never promoted to a production value, and
are not read anywhere in this task's code. `alignment_anchor_evidence_consumed.rm014_diagnostic_numeric_anchor_injected`
is recorded as `false` in the sanitized evidence and independently verified
by `scripts/verify_final_real_corpus_replay.py`.

## No-evidence-promotion proof

- `compatibility.py`, `eligibility.py`, `metrics.py`, `ranking.py`,
  `policies.py` are byte-identical to the starting HEAD (`git diff` empty —
  independently checked by `verify_final_real_corpus_replay.py`).
- `analysis_confidence`, beat/downbeat confidence, and every hard gate are
  computed by the exact same unmodified `compatibility.evaluate_pair_compatibility`
  used before this task.
- All-In-One functional/downbeat outputs and madmom outputs remain
  benchmark/oracle diagnostics; neither was promoted to canonical evidence
  this pass, and neither was rerun.
- No threshold was relaxed, no gate was reordered, and no RM id received
  special-cased code.

## Validation

`python tools/p0m3/audio_render_shootout/scripts/verify_final_real_corpus_replay.py`:
**ALL CHECKS PASS.** Covers: corpus track count (100), no audio
decode/new-analyzer import in any changed/new source file (import/call-line
scan, not a prose-docstring scan), the transition-policy pre-flight
verifier (220/220), sanitized-evidence shape and privacy (no Windows/WSL/
Linux-home path shape, no audio file extension anywhere in the sanitized
JSON), independent re-derivation of both V1/V2 strict survivor counts
directly from cached analysis (byte-for-byte reproducible, not merely
re-read from the output file), independent re-planning of every claimed
survivor through the unmodified canonical evaluator (vacuously true here —
zero survivors — and re-exercised structurally), and working-tree
immutability of the five untouched policy modules.

## Privacy / scope

- Corpus root: `owner_music_input` only, unchanged, not broadened.
- No audio decoded, no new analyzer run, no render, no Signalsmith, no
  Rubber Band, no owner listening pack, no P1 work, no `main` merge.
- The sanitized replay evidence (`results/final_real_corpus_replay_sanitized.json`)
  contains opaque RM ids, gate-result tri-state labels, numeric gaps/ratios,
  and enum reason codes only — no filename, path, artist, title, album, raw
  embedded tag, audio hash, or audio bytes anywhere.
- `real_music/work_local/` (corpus analysis, id map, manifest) remains
  local-only/gitignored, unchanged this pass.

## Files

- `docs/research/P0-M3-R3-FINAL-REAL-CORPUS-REPLAY.md` (this document)
- `tools/p0m3/transition_policy/policy/contract.py` (pre-flight fix)
- `tools/p0m3/transition_policy/policy/boundary.py` (per-side invalid flags)
- `tools/p0m3/transition_policy/verify.py` (41 new mutation assertions)
- `tools/p0m3/transition_policy/results/*.json`, `results/SUMMARY.md`
  (regenerated)
- `tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py`
  (`alignment_anchor_fields()` — selector-layer separation integration)
- `tools/p0m3/audio_render_shootout/scripts/final_real_corpus_replay.py`
  (new — replay engine)
- `tools/p0m3/audio_render_shootout/scripts/verify_final_real_corpus_replay.py`
  (new — verifier)
- `tools/p0m3/audio_render_shootout/results/final_real_corpus_replay_sanitized.json`
  (new — sanitized replay evidence)

## PM review request

Please independently verify:

1. Run `python tools/p0m3/transition_policy/run_benchmark.py` and
   `python tools/p0m3/transition_policy/verify.py`; confirm `RESULT: ALL
   ASSERTIONS PASS` (220/220).
2. Run `python tools/p0m3/audio_render_shootout/scripts/verify_final_real_corpus_replay.py`;
   confirm `RESULT: ALL CHECKS PASS`.
3. Open `results/final_real_corpus_replay_sanitized.json`; confirm
   `V1.strict_full_dj_survivor_count == 0`, `V2.strict_full_dj_survivor_count
   == 0`, `result == "R3_FINAL_PARTIAL_NO_VALID_V1_V2"`, and
   `canonical_planner_full_dj_withheld == 0` in both categories (proof that
   the alignment-anchor gate was never the deciding rejection for any
   candidate).
4. Confirm `git diff` shows zero changes to `policy/compatibility.py`,
   `policy/eligibility.py`, `policy/metrics.py`, `policy/ranking.py`,
   `policy/policies.py`.
5. Confirm no RM id, owner-private timestamp, or environment-local path
   appears anywhere in the diff or in
   `results/final_real_corpus_replay_sanitized.json`.

## Result

**`R3_FINAL_PARTIAL_NO_VALID_V1_V2`**

## R3 closeout status

P0-M3-R3 ENGINEERING COMPLETE — FINAL NEGATIVE/PARTIAL FEASIBILITY. No
further analyzer/oracle/calibration loop is authorized by this result. PM
will independently verify and close Issue #7 as the final P0-M3-R3
negative/PARTIAL feasibility result.
