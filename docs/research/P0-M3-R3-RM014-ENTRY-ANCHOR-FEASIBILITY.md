# P0-M3-R3 — RM014 incoming-entry anchor feasibility

Status date: 2026-08-17

Binding task: Issue #7 PM comment "PM CLOSEOUT — RM041->RM014
EVIDENCE-STABILITY PRIVACY REPAIR ACCEPTED; INCOMING-ENTRY ANCHOR
FEASIBILITY NEXT" (comment id `5310893724`).

Starting HEAD: `b181f4274d6f675deba17f3e78b7021e968768db`.

This pass is **diagnostic only**. No new entry was written back into R2.
The canonical RM014 incoming-entry evidence remains **0 ms**.

## Result

**`SEPARATE_ENTRY_AND_ALIGNMENT_ANCHOR_JUSTIFIED`**

The evidence below supports treating a later, machine-stable downbeat as a
separate *alignment anchor* candidate concept while **preserving the
audible incoming entry at 0 ms**, rather than moving the entry itself
(`REANCHOR_EXISTING_ENTRY_PLAUSIBLE`). Two things drive this, both measured
this pass, not assumed: (1) the region that would be discarded if the entry
itself were moved shows an elevated relative vocal-band-energy presence
(87th-92nd percentile of the whole track) even though it is quieter and
sparser overall — content-preservation risk, not a clearly disposable
lead-in; (2) moving the anchor improves the RM014-side downbeat/root-mode
*self-consistency* but does **not** improve, and in fact worsens, the
RM041<->RM014 harmonic *pair* relation (see Harmonic re-evaluation below) —
so re-anchoring ENTRY would not even resolve the problem it might appear to
target. This is a diagnostic conclusion only; it defines no production
threshold and mutates no gate.

## Scope

RM014 private audio only (content-preservation and harmonic re-evaluation
steps). RM041 audio was **not** re-decoded this pass — the harmonic
re-evaluation reuses the already-accepted RM041 exit cells from
`pair_stability/results/harmonic_sensitivity.json` verbatim. No All-In-One
rerun (all downbeat/structure evidence reused from the 10 already-accepted
`pair_stability/results/raw_runs/*.json` files). No corpus rerun, no
render, no Signalsmith, no Rubber Band, no owner listening pack, no P1.

## Intro interval (unanimous across all 5 seeds)

Every one of RM014's 5 All-In-One seeds agrees exactly (0 ms difference) on
the end of the leading `intro`-labeled segment run: **0 ms -> 19860 ms**.
This is the unanimous functional-intro interval used for downbeat
clustering below. (All 5 seeds also agree the leading intro is itself split
into two literal `AnalysisResult.segments` rows, e.g. `[0, ~10-20 ms]` then
`[~10-20 ms, 19860 ms]`, both labeled `intro` — a segmentation artifact, not
a second functional section.)

## Machine-derived downbeat clusters

All 5 RM014 seeds' downbeats strictly inside `[0, 19860)` ms were pooled and
merged into clusters at a 100 ms tolerance (justification: the accepted
RM041<->RM014 stability pass measured RM014's own baseline-vs-other
downbeat-grid p90 at 10 ms with ~96% coverage at 100 ms, and RM014's local
downbeat interval is ~1840-1950 ms at seeds 2/3/4 — 100 ms is generous
cross-seed jitter tolerance that is nowhere near large enough to merge two
different bars). 15 clusters resulted; the top 6 by the task's mandated
ranking order (5/5 support desc, then spread asc, then madmom disagreement
asc, then earliest time asc):

| Rank | Support | Center | Per-seed (s0..s4, ms) | Spread | Nearest madmom | madmom err | % of intro preceding |
|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | 5/5 | 18650.0 ms | 18650, 18650, 18650, 18650, 18650 | 0.0 ms | 18360.0 ms | 290.0 ms | 93.9% |
| 2 | 5/5 | 7374.0 ms | 7370, 7370, 7370, 7380, 7380 | 10.0 ms | 7360.0 ms | 14.0 ms | 37.1% |
| 3 | 4/5 | 16380.0 ms | 16380, 16380, 16380, 16380, — | 0.0 ms | 16030.0 ms | 350.0 ms | 82.5% |
| 4 | 4/5 | 14110.0 ms | 14100, 14090, 14140, 14110, — | 50.0 ms | 13590.0 ms | 520.0 ms | 71.1% |
| 5 | 3/5 | 10940.0 ms | 10940, 10940, —, —, 10940 | 0.0 ms | 10730.0 ms | 210.0 ms | 55.1% |
| 6 | 3/5 | 3786.7 ms | —, —, 3790, 3780, 3790 | 10.0 ms | 3860.0 ms | 73.3 ms | 19.1% |

Full 15-cluster table: `results/intro_clusters.json`.

### Verifying vs. discrepancy-checking the PM's forensic observation

The PM's inspection cited a likely high-quality cluster near **~7.36-7.38
s** with **5/5 seed support** and madmom near **~7.36 s**. Independently
derived: **confirmed as a real, tight, 5/5-support cluster** — center
7374.0 ms (7.374 s), spread only 10 ms, nearest madmom downbeat 7360.0 ms
(7.360 s), abs. error 14 ms. This is genuinely the *best-matching-to-madmom*
5/5 cluster.

**Discrepancy**: under the task's own mandated strict ranking order (5/5
support first, then *smallest spread*, THEN madmom disagreement), this
cluster ranks **#2, not #1**. The 18650.0 ms cluster has zero cross-seed
spread (all 5 seeds report the identical value to the millisecond) and also
has 5/5 support, so it wins on tie-break criterion #2 despite having 20x
worse madmom disagreement (290 ms vs 14 ms). The PM's underlying
observation about the 7.36-7.38 s cluster's quality is correct; the
assumption that it is the single best-ranked candidate is not, once the
task's own tie-break order is applied mechanically. Both are carried
forward as the "best one or two" candidates for the remaining diagnostics,
which is what surfaced this ranking-order sensitivity in the first place.

## Skipped-content preservation analysis

RM014 whole-track duration: 208.256 s. Measured via 1-second-binned RMS,
onset density, a spectral-band "vocal-activity proxy" (300-3400 Hz STFT
energy fraction — a heuristic, not a vocal separator/detector), an
HPSS-percussive-RMS "bass/percussion-activity proxy", sub-bass (20-150 Hz)
energy fraction, and spectral centroid, each region's mean compared against
its own whole-track per-bin percentile distribution.

| Candidate | Region | Duration skipped | RMS %ile | Onset-density %ile | Vocal-band %ile | Sub-bass %ile | Classification |
|---|---|---:|---:|---:|---:|---:|---|
| Rank 1 (18650 ms) | 0 -> 18650 ms | 18.65 s (93.9% of intro) | 15.3 | 15.8 | **87.1** | 15.3 | `LOW_INFORMATION_MUSICAL_INTRO` |
| Rank 2 (7374 ms) | 0 -> 7374 ms | 7.37 s (37.1% of intro) | 22.5 | 22.0 | **92.3** | 4.8 | `LOW_INFORMATION_MUSICAL_INTRO` |
| Full intro (context) | 0 -> 19860 ms | 19.86 s (100%) | 15.8 | 15.8 | 87.1 | 15.3 | `LOW_INFORMATION_MUSICAL_INTRO` |

Full detail: `results/content_preservation.json`.

**The primary RMS/onset-density-based classification alone would read as
"low information," but this is not the whole picture.** Both skipped
regions register a strongly elevated relative vocal-band-energy fraction
(87th-92nd percentile of the entire track) despite being quiet and sparse
overall by RMS/onset density — a pattern consistent with a
vocal-forward/vocal-led intro over sparse instrumentation (e.g. a cold-open
vocal hook), not consistent with silence or a purely instrumental pad.
Per the task's explicit constraint, active musical content must not be
auto-labeled disposable to satisfy a downbeat gate: **neither region
qualifies for `CLEAR_NON_MUSICAL_LEAD_IN`** under the stated methodology
(that label requires BOTH RMS and onset density at or below the 10th
percentile, and neither region gets close — 15-23rd percentile on both).
The honest reading is that both candidates discard content with a
disproportionately present vocal signal relative to the rest of the track,
which is a real content-preservation cost, larger for the rank-1 (18.65 s,
93.9% of the intro) candidate than the rank-2 (7.37 s, 37.1% of the intro)
candidate.

## Harmonic re-evaluation

Reused the identical bounded methodology already accepted for Issue #7
(`wsl_bounded_audio_oracles.py::cqt_key_at`/`_profile_key`, byte-for-byte
unchanged) and the unmodified `select_real_music_pairs.harmonic_relationship`,
swept across the same window lengths `{10, 15, 20, 30}` s and perturbations
`{-1000, -500, 0, +500, +1000}` ms as the accepted 0 ms pass, rooted at each
of the top-2 candidates instead of 0 ms. RM041 exit audio was not
re-decoded; its already-accepted cells were reused verbatim for the pair
comparison.

### Entry-side self-consistency (root/mode estimate stability)

| Boundary | Cells measured | Distinct root/modes | Modal agreement | High-confidence cells |
|---|---:|---:|---:|---:|
| Accepted 0 ms (baseline) | 12/20 | 4 | 0.4167 | 3/20 |
| Rank 1 (18650 ms) | 20/20 | 2 (`G major`x15, `G minor`x5) | 0.75 | 15/20 |
| Rank 2 (7374 ms) | 20/20 | 2 (`C minor`x15, `G major`x5) | 0.75 | 18/20 |

Both candidates measurably improve entry-side root/mode self-consistency:
every one of the 20 window/perturbation cells is now measurable (0 ms had
8 `OUT_OF_AVAILABLE_AUDIO_RANGE` cells at the negative perturbations, since
there is no audio before track start), distinct root/mode count drops from
4 to 2, and high-confidence cells roughly quintuple. This part of the PM's
implicit hypothesis (a later anchor gives cleaner key evidence) is
confirmed by measurement.

### Pair relation vs. the accepted RM041 exit (D minor) — this does NOT improve

| Boundary | COMPATIBLE | INCOMPATIBLE | UNKNOWN | (of 20 matched cells) |
|---|---:|---:|---:|---|
| Accepted 0 ms (baseline, 12 valid/in-range cells) | 3 | 3 | 6 | mixed/ambiguous |
| Rank 1 (18650 ms) | 4 | 14 | 2 | dominantly INCOMPATIBLE |
| Rank 2 (7374 ms) | 0 | 18 | 2 | almost entirely INCOMPATIBLE |

At 0 ms, RM041(D minor)<->RM014(entry) was genuinely ambiguous across
window lengths (see the already-accepted `P0-M3-R3-RM041-RM014-EVIDENCE-STABILITY.md`).
Moving the diagnostic anchor to either candidate does **not** resolve this
ambiguity toward `COMPATIBLE`; it moves it toward a *more confidently
measured* but *more decisively negative* `INCOMPATIBLE` reading. Root cause,
observable directly in the per-cell data: at 18650 ms RM014 mostly resolves
to `G major`/`G minor` and at 7374 ms mostly to `C minor` — neither is the
`G minor` result that matched the single accepted independent-oracle
30 s-window call at 0 ms.

**Answer to the task's explicit question**: does moving the diagnostic
incoming anchor materially improve harmonic root/mode *stability*? Yes, for
RM014's own entry-side key estimate in isolation. Does it improve the
*pair*-level harmonic compatibility that actually gates `FULL_DJ_BLEND`?
No — it makes the RM041->RM014 harmonic relationship read more decisively
`INCOMPATIBLE`. These are two different questions with two different
answers, and conflating them would overstate the case for re-anchoring.

Full detail: `results/harmonic_reeval.json`.

## Case A — REANCHOR ENTRY (not implemented, evaluated only)

Moving the incoming-entry point itself to the candidate anchor:

- **Incoming content omitted**: 7.37 s (37.1% of the detected intro) at
  rank 2, or 18.65 s (93.9% of the intro) at rank 1 — both regions carry a
  measured 87th-92nd-percentile relative vocal-band presence (see above),
  so this is not a clean silence-trim.
- **Downbeat stability**: excellent at either candidate — 5/5 exact-or-near
  cross-seed agreement, vs. the accepted stability report's finding that
  the current 0 ms entry has a genuinely split two-cluster cross-seed
  downbeat disagreement (seeds 0/1 vs. 2/3/4).
- **Harmonic stability**: entry-side self-consistency improves; pair
  compatibility with RM041's exit does not improve and reads more
  decisively `INCOMPATIBLE` (see above).
- **Functional-section role**: both candidates remain inside the SAME
  `intro` functional label (93.9% / 37.1% through it) — moving entry to
  either point starts playback later *within* the intro, not at a new
  section boundary (e.g. not at the `verse` that begins at 19860 ms).
- **Would the existing R2 data model represent this without a contract
  change?** Yes, trivially — Case A just moves
  `next_track_entry_window_ms`/`incoming_effective_content_start_ms` (and,
  under the current coupled builder logic, the alignment-target fields too)
  to the new single timestamp. This is exactly today's existing coupled
  behavior; no schema change is needed for Case A.

## Case B — PRESERVE ENTRY + SEPARATE ALIGNMENT ANCHOR (not implemented, evaluated only)

Keeping the audible incoming entry at the current accepted 0 ms while using
a later stable downbeat as a distinct alignment reference:

- **Intro preserved?** Yes — full audible content retained, including the
  measured elevated vocal-band presence in the first ~7-19 s.
- **Stable downbeat available?** Yes — either candidate (5/5 support,
  14-290 ms madmom agreement depending on which) is available purely as a
  reference point, independent of where playback audibly begins.
- **Required delta between entry and anchor**: 7374 ms or 18650 ms,
  depending on candidate — must be represented explicitly, never silently
  dropped or approximated to 0.
- **Does the current R2 contract already represent this separation?**
  **No — proven from source, not assumed.** Read directly (unmodified) from
  `tools/p0m3/transition_policy/policy/contract.py`'s
  `build_boundary_transition_decision`:
  ```python
  incoming_beat_target = entry_candidate["t_ms"] if entry_candidate.get("beat_downbeat_aligned") else None
  incoming_downbeat_target = incoming_beat_target
  ...
  entry_window = {"t_start_ms": entry_candidate["t_ms"], "t_end_ms": entry_candidate["t_ms"]}
  ```
  Both `incoming_beat_alignment_target_ms`/`incoming_downbeat_alignment_target_ms`
  AND `next_track_entry_window_ms` are derived from the SAME single
  `entry_candidate["t_ms"]` value on the SAME candidate object
  (`policy/boundary.py`'s `entry_candidates = incoming_track["candidates"]`,
  each with exactly one `t_ms`). There is no field on an incoming-entry
  candidate today that can hold an alignment reference distinct from its
  own entry point. So the current R2 contract genuinely cannot represent
  Case B — this is a structural coupling in the builder, confirmed by
  reading the source, not an assumption.
- **Minimum future contract concept needed** (description only — not
  implemented, `contract.py`/`boundary.py` unmodified this pass):
  `PlannerDecision`'s dataclass SHAPE already has the independent fields
  Case B would need
  (`incoming_effective_content_start_ms`/`next_track_entry_window_ms` vs.
  `incoming_beat_alignment_target_ms`/`incoming_downbeat_alignment_target_ms`)
  — no new field is required there. The actual minimum gap is smaller and
  more localized: an additive, optional field on the incoming-entry
  candidate object (e.g. `alignment_target_ms`, alongside the existing
  `t_ms`/`onset_window_ms`/`beat_downbeat_aligned`), plus updating the two
  lines quoted above in `build_boundary_transition_decision` to prefer that
  field when present and fall back to today's `t_ms`-reuse behavior
  otherwise. This would be additive and backward-compatible (no existing
  field renamed or removed) — but it is a real, non-zero contract concept
  that does not exist today, and is out of scope to implement this pass.

## Architectural verdict

`SEPARATE_ENTRY_AND_ALIGNMENT_ANCHOR_JUSTIFIED` (diagnostic only). The
downbeat evidence for a later anchor is strong and the current 0 ms entry's
own downbeat evidence is comparatively weak (per the already-accepted
stability report), which argues for *some* form of later reference point.
But the measured vocal-band content-preservation cost and the *lack* of
harmonic-pair improvement both argue against moving the audible ENTRY
itself. Preserving entry while carrying a separate, explicit alignment
reference is the option best supported by this pass's combined evidence —
with the explicit caveat that it solves the downbeat/rhythm-alignment
instability only; the RM041<->RM014 harmonic-pair question remains open
(and, per this pass, reads more decisively unfavorable at either candidate
anchor) and is unaffected by this choice either way.

## Validation

`tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/verify_entry_anchor_feasibility.py`:
**117/117 PASS.** Covers: intro interval unanimity, deterministic ranking
order, required fields on every cluster, content-preservation region
coverage (top-2 candidates + full-intro context) and classification-enum
validity, the "disposable label requires both RMS and onset <=10th
percentile" safety invariant, harmonic re-evaluation window/perturbation
coverage (20/20 cells per candidate) and presence of the vs.-accepted-0ms
comparison, absence of any `allin1`/render/Signalsmith/RubberBand/owner-
listening token or RM041-mapping lookup in this directory's Python sources,
and absence of Windows/WSL path shapes or audio-file extensions in every
committed source and result file (self-referential exclusions applied to
the verifier's own source and its own prior output file, mirroring the
already-accepted fix in `pair_stability/verify_pair_stability.py`).

Git-level checks (run directly): `compatibility.py`, `contract.py`,
`boundary.py`, and `select_real_music_pairs.py` are byte-identical to the
starting HEAD; `pair_stability/` results are byte-identical to the starting
HEAD (no rerun); working branch is `research/p0-feasibility`; `main` is
unrelated/unreachable from any commit made this session.

## Privacy / scope

- Exactly one track's audio was decoded: RM014. RM041 audio was never
  loaded; its already-accepted harmonic cells were reused verbatim.
- No whole 19-track or 100-track corpus rerun; no `allin1.analyze` call.
- Committed evidence contains RM ids, timestamps, and numeric measurements
  only — no source filename, path, artist, title, album, raw tag, audio
  hash, or audio bytes. The private opaque-id -> local-path mapping was
  read only to load RM014's audio and was never printed or written to any
  committed file.
- No Signalsmith, Rubber Band, transition render, or owner listening pack.
- No R2 gate change, no `compatibility.py`/`contract.py`/`boundary.py`/
  `select_real_music_pairs.py` edit, no P1 work, no `main` merge.

## Files

- `tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/derive_intro_clusters.py`
- `tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/content_preservation_analysis.py`
- `tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/harmonic_reeval_candidates.py`
- `tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/verify_entry_anchor_feasibility.py`
- `tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/EXACT_COMMANDS.md`
- `tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/*.json`
