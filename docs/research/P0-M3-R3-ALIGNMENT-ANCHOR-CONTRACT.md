# P0-M3-R3 — Alignment-anchor contract separation

Status date: 2026-08-17

Binding task: "P0-M3-R3 ALIGNMENT-ANCHOR CONTRACT SEPARATION" (Claude Desktop
Code-tab session, Sonnet 5 High/Extended-Thinking, sub-agents OFF). This is
**technical task 1 of the final 2-task R3 closeout**; the only planned
engineering task after this one is the **FINAL REAL-CORPUS REPLAY** (not
performed in this session).

Starting HEAD: `44d353e4c18ed56987d824ffb051987f5ae09634` (verified before
any edit).

This pass implements, generically, the architectural distinction the
accepted RM014 diagnostic (`docs/research/P0-M3-R3-RM014-ENTRY-ANCHOR-FEASIBILITY.md`,
result `SEPARATE_ENTRY_AND_ALIGNMENT_ANCHOR_JUSTIFIED`) identified: an
incoming track's audible/source **entry** and its beat/downbeat **alignment
target** are two different concepts. RM014's own timestamps are **not**
used anywhere in this pass — this repair is generic production/planner
contract engineering, per the task's explicit instruction not to
special-case RM014.

## Contract before

`policy/boundary.py`'s `build_boundary_transition_decision` (via
`policy/contract.py`) used a single field, `entry_candidate["t_ms"]`, for
THREE distinct purposes simultaneously:

```python
incoming_beat_target = entry_candidate["t_ms"] if entry_candidate.get("beat_downbeat_aligned") else None
incoming_downbeat_target = incoming_beat_target
...
entry_window = {"t_start_ms": entry_candidate["t_ms"], "t_end_ms": entry_candidate["t_ms"]}
```

1. the audible/source entry time (`next_track_entry_window_ms`)
2. the beat alignment reference (`incoming_beat_alignment_target_ms`)
3. the downbeat alignment reference (`incoming_downbeat_alignment_target_ms`)

There was no candidate-level field that could hold an alignment reference
distinct from the entry point itself — a track could not represent "start
audibly at 0 ms, but align to a stable downbeat at 8000 ms" without either
fabricating a fake anchor at 0 ms or moving the audible entry itself (and
losing real intro content, exactly the RM014 diagnostic's concern).

`policy/boundary.py`'s R5 (PM REVIEW #3) FULL_DJ_BLEND gate compounded this
by reading the raw `beat_downbeat_aligned` boolean directly
(`boundary_alignable = bool(exit_c.get("beat_downbeat_aligned")) and
bool(entry_c.get("beat_downbeat_aligned"))`), so there was no way to
authorize `FULL_DJ_BLEND` from an explicit, separate alignment anchor at
all — only from the coupled boolean.

## Contract after

`policy/contract.resolve_alignment_targets(candidate)` is the one canonical
helper (A1) used by every place that resolves a candidate's alignment
targets — `build_transition_decision` (legacy single-track outgoing side),
`build_boundary_transition_decision` (both outgoing and incoming sides,
A6), and `policy/boundary.py`'s per-boundary `FULL_DJ_BLEND` alignability
gate (A5).

```python
def resolve_alignment_targets(candidate: dict):
    has_explicit_beat = "beat_alignment_target_ms" in candidate
    has_explicit_downbeat = "downbeat_alignment_target_ms" in candidate
    if has_explicit_beat or has_explicit_downbeat:
        beat_target = candidate.get("beat_alignment_target_ms") if has_explicit_beat else None
        downbeat_target = candidate.get("downbeat_alignment_target_ms") if has_explicit_downbeat else None
        return beat_target, downbeat_target, "EXPLICIT"
    if candidate.get("beat_downbeat_aligned"):
        t_ms = candidate["t_ms"]
        return t_ms, t_ms, "LEGACY_T_MS"
    return None, None, "NONE"
```

`candidate["t_ms"]` keeps its existing, unchanged meaning everywhere else
(audible/source entry or exit time). `next_track_entry_window_ms` /
`incoming_effective_content_start_ms` are derived ONLY from `t_ms` /
`onset_window_ms` (unchanged code paths, A2) — never from a resolved
alignment target, so a later alignment anchor never moves the audible
entry window.

## Target resolution semantics (A1)

- **EXPLICIT mode**: if EITHER `beat_alignment_target_ms` or
  `downbeat_alignment_target_ms` is present on the candidate, EXPLICIT mode
  applies. A missing field is **never backfilled** from `t_ms` or from the
  other field — a partially explicit candidate stays partially known
  (proven by the PARTIAL EXPLICIT test, below).
- **LEGACY mode**: only when NEITHER explicit field is present. Reproduces
  the pre-existing `beat_downbeat_aligned` behavior exactly — both targets
  equal `t_ms` when true, else both `None`. This is what keeps TX-01..07
  behaviorally unchanged (they use only the legacy boolean).
- **EXPLICIT always wins over LEGACY**, even when both are present on the
  same candidate (proven by a direct unit-style test in `verify.py`).

## A4 — invalid alignment references fail closed

For an incoming candidate, if a resolved beat or downbeat alignment target
is earlier than the candidate's own `t_ms` (audible entry), that boundary's
`FULL_DJ_BLEND` alignment evidence is rejected — reason code
`INVALID_INCOMING_ALIGNMENT_TARGET_PRECEDES_ENTRY` — and `FULL_DJ_BLEND` is
withheld exactly as if no alignment evidence existed at all
(`FULL_DJ_BLEND_WITHHELD_NO_BOUNDARY_ALIGNMENT_EVIDENCE`). The timestamp
itself is **never clamped or rewritten**; `incoming_beat_alignment_target_ms`
still reports the raw (invalid) value honestly in the `PlannerDecision` —
only the FULL_DJ_BLEND authorization is refused. No arbitrary
maximum-entry-to-anchor delta was introduced (not requested by this task).

## A5 — FULL_DJ boundary alignability via resolved-target presence

`policy/boundary.py`'s per-boundary gate is now:

```python
boundary_alignable = (
    exit_beat_target is not None and exit_downbeat_target is not None
    and entry_beat_target is not None and entry_downbeat_target is not None
    and not invalid_incoming_alignment
)
```

replacing the prior raw-boolean check. Pair-level beat/downbeat
*confidence* (`policy/compatibility.py`, unmodified) remains a separate,
still-required gate — this repair only changes how the SELECTED
exit/entry candidates' own renderable targets are proven present.

## A7 — trace provenance

Every boundary candidate in `candidate_rank_trace` (not only the winner)
now carries: `incoming_entry_t_ms`, `incoming_beat_alignment_target_ms`,
`incoming_downbeat_alignment_target_ms`, `incoming_alignment_target_source`
(`EXPLICIT | LEGACY_T_MS | NONE`), `incoming_alignment_separate_from_entry`
(bool), and the outgoing-side resolved targets +
`outgoing_alignment_target_source` for symmetry. New reason codes:
`SEPARATE_INCOMING_ALIGNMENT_ANCHOR_PRESENT`,
`ENTRY_AND_ALIGNMENT_ANCHOR_COINCIDE`, `PARTIAL_INCOMING_ALIGNMENT_EVIDENCE`,
`INVALID_INCOMING_ALIGNMENT_TARGET_PRECEDES_ENTRY`.

`PlannerDecision`'s own field set is **unchanged** (A8) — no redundant
generic `alignment_target_ms` field was added; the existing
`incoming_beat_alignment_target_ms` / `incoming_downbeat_alignment_target_ms`
/ `next_track_entry_window_ms` fields now simply resolve correctly, per the
candidate-level contract repair above.

## TX-08 — separation proof (A9)

New metadata-only fixture, generic synthetic data, no RM IDs:

- Incoming candidate `TX08-IN-ZERO-SEPARATE-ANCHOR`: `t_ms=0`,
  `beat_downbeat_aligned=false` (deliberately NOT the legacy boolean —
  proves EXPLICIT mode alone is sufficient), `beat_alignment_target_ms=8000`,
  `downbeat_alignment_target_ms=8000`.
- Outgoing candidate `TX08-OUT-1`: `t_ms=180000`, `beat_downbeat_aligned=true`
  (legacy resolution on the outgoing side, per A6).
- Pair: honestly fully compatible under the EXISTING, unmodified
  `compatibility.py` gates (genre/tempo/beat/downbeat confidence/structure/
  texture/vocal/bass/analysis-confidence/harmonic all pass).

Computed `PlannerDecision` (`results/boundary_planning.json`, `TX-08`):

| Field | Value |
|---|---|
| `selected_incoming_entry_candidate_id` | `TX08-IN-ZERO-SEPARATE-ANCHOR` |
| `next_track_entry_window_ms` | `{"t_start_ms": 0, "t_end_ms": 0}` |
| `incoming_beat_alignment_target_ms` | `8000` |
| `incoming_downbeat_alignment_target_ms` | `8000` |
| `incoming_effective_content_start_ms` | `0` |
| `allowed_transition_class_set` | includes `FULL_DJ_BLEND` |
| `beat_alignment_action` | `ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET` |
| `bar_alignment_action` | `ALIGN_OUTGOING_DOWNBEAT_TARGET_TO_INCOMING_DOWNBEAT_TARGET` |

The audible incoming entry remains at `0 ms`; no incoming source content is
skipped; the alignment anchor (`8000 ms`) is used purely as a distinct
reference. `FULL_DJ_BLEND` is authorized because both sides resolve real
beat/downbeat targets — never because the entry itself moved.

## Legacy TX-01..07 regression (A11)

`policy/boundary.py`/`policy/contract.py` reproduce the exact prior mapping
for any candidate using only the legacy `beat_downbeat_aligned` boolean
(LEGACY mode == old behavior byte-for-byte). Evidence:

- `git diff` shows **zero** changes to `policy/compatibility.py`,
  `policy/eligibility.py`, `policy/metrics.py`, `policy/ranking.py`, or
  `policy/policies.py` — none of the touched files' behavior for
  TX-01..07 depends on anything beyond `resolve_alignment_targets`'s
  LEGACY-mode path, which is provably identical to the prior inline
  expressions.
- `results/boundary_planning.json`'s diff for TX-01..07 shows **only**
  additive fields (`incoming_entry_t_ms`, `incoming_*_alignment_target_ms`,
  `*_alignment_target_source`, `incoming_alignment_separate_from_entry`)
  and two new, honest, additive reason codes
  (`ENTRY_AND_ALIGNMENT_ANCHOR_COINCIDE`) — every previously-existing field
  value (`selected_outgoing_exit_candidate_id`,
  `selected_incoming_entry_candidate_id`, `decision_type`,
  `allowed_transition_class_set`, `next_track_entry_window_ms`,
  `outgoing_content_preservation_target`, `required_tempo_ratio`,
  `required_pitch_shift_semitones`, `permitted_pitch_shift_semitones_*`,
  `beat_phase_relation`, `bar_phase_relation`) is byte-identical.
- `results/decision_traces.json`, `results/metrics.json`,
  `results/sensitivity_matrix.json`, `results/order_invariance.json`,
  `results/pair_compatibility.json`, `results/mutation_pair_report.json`,
  `results/playthrough_demo.json` show **no diff at all** — none of the 14
  timing fixtures (A-N) or 13 pair fixtures are affected.
- Every pre-existing `verify.py` assertion for TX-01, TX-02, TX-03, TX-04,
  TX-05, TX-06, TX-07 (selected winner, allowed transition class set,
  alignment targets on both sides, tempo ratio, pitch envelope, phase
  relation, order invariance) continues to `PASS` unchanged.
- Downstream consumers of `PlannerDecision` outside `transition_policy`
  (`tools/p0m3/audio_render_shootout/fixtures/generate_planner_decisions.py`,
  which calls `plan_transition_boundary` directly) were checked read-only
  against their already-committed `planner_decisions/R3-{A,B,C,D}.json`:
  every one of `decision_type`, `allowed_transition_class_set`,
  `selected_outgoing_exit_candidate_id`,
  `selected_incoming_entry_candidate_id`,
  `outgoing_content_preservation_target`, `required_tempo_ratio`,
  `required_pitch_shift_semitones`, `beat_alignment_action`,
  `bar_alignment_action`, `outgoing_beat_alignment_target_ms`,
  `incoming_beat_alignment_target_ms`,
  `outgoing_downbeat_alignment_target_ms`,
  `incoming_downbeat_alignment_target_ms`, `next_track_entry_window_ms`,
  `incoming_effective_content_start_ms`,
  `permitted_tempo_ratio_max_deviation`,
  `permitted_pitch_shift_semitones_min/max` matched exactly (`ALL KEY
  FIELDS MATCH: True`). Those committed files were **not** regenerated or
  modified — this was a read-only regression check, out of this task's
  scope per `select_real_music_pairs.py`/real-corpus immutability (A12).

## Fail-closed mutation tests (A10)

10 new checks added under `verify.py`'s "P0-M3-R3 A1-A9: alignment-anchor
contract separation" section:

1. **EXPLICIT SEPARATION** (TX-08): entry stays `0ms`; alignment targets
   report the later `8000ms` explicit value; `FULL_DJ_BLEND` authorized.
2. **LEGACY COMPATIBILITY**: TX-06's legacy `beat_downbeat_aligned=true`
   candidate resolves `source=LEGACY_T_MS`, both targets `== t_ms`.
3. **EXPLICIT OVERRIDES LEGACY**: a synthetic candidate with BOTH explicit
   fields AND `beat_downbeat_aligned=true` resolves `source=EXPLICIT` with
   the explicit values, not `t_ms`.
4. **PARTIAL EXPLICIT**: a TX-08 variant missing
   `downbeat_alignment_target_ms` resolves `incoming_downbeat_alignment_target_ms
   is None` (never backfilled from `t_ms`) and withholds `FULL_DJ_BLEND`,
   with `PARTIAL_INCOMING_ALIGNMENT_EVIDENCE` in the trace.
5. **INVALID BEFORE ENTRY**: a synthetic candidate with `t_ms=5000` and an
   explicit `beat_alignment_target_ms=1000` (before entry) fails closed —
   `FULL_DJ_BLEND` withheld, `INVALID_INCOMING_ALIGNMENT_TARGET_PRECEDES_ENTRY`
   in the trace, and the raw `1000` value is still honestly reported (never
   clamped to `5000`).
6. **ZERO ENTRY DOES NOT REQUIRE PHRASE-SKIP EVIDENCE**: TX-08's `0ms`
   entry is accepted via `ENTRY_AT_TRACK_START`, never
   `ENTRY_SKIPS_MEANINGFUL_INTRO_WITHOUT_EVIDENCE`, despite its `8000ms`
   alignment anchor.
7. **ENTRY WINDOW NEVER FOLLOWS ALIGNMENT TARGET**: TX-08's entry window
   (`0`) is strictly less than its alignment target (`8000`).
8. **ALIGNMENT TARGET NEVER CHANGES `incoming_effective_content_start_ms`**:
   stays `0` despite the `8000ms` anchor.
9. **Pair compatibility gates unchanged**: TX-08's boundary is genuinely
   `eligible_for_dynamic_mix` under the existing, unmodified
   `compatibility.py` gate (no gate was weakened to make TX-08 pass).
10. **Preservation safety unchanged**: TX-08's preservation target still
    respects the existing `SEAMLESS_FULL_TRACK_DEFAULT` floor (`>=0.95`).

## PlannerDecision output (A8)

No new top-level `PlannerDecision` field was added. The repair is entirely
at candidate/planning semantics
(`policy/contract.resolve_alignment_targets`) and at the boundary planner's
internal alignability computation (`policy/boundary.py`) — exactly the
"additive, optional field on the incoming-entry candidate object... update
the two lines... to prefer that field when present and fall back to
today's t_ms-reuse behavior otherwise" scope the RM014 diagnostic
identified as the minimum gap, generalized to both sides (A6) and hardened
with the fail-closed validity check (A4) and full trace provenance (A7).

## Validation

```
python tools/p0m3/transition_policy/run_benchmark.py
python tools/p0m3/transition_policy/verify.py
```

**179 of 179 assertions PASS** (up from PM REVIEW #3's 151 — all 151
retained and re-verified unchanged, plus 28 new checks covering A1-A10).
`transition_fixture_count` is now 8 (`TX-01..08`); `fixtures.json` (14) and
`pair_fixtures.json` (13) are unchanged.

Structural/scope checks (all `PASS`, reproduced from `verify.py`'s output):
timing fixture count == 14; pair fixture count == 13; transition boundary
fixture count == 8; no ground-truth-only field is read by policy decision
code (AST-based); no Signalsmith/Rubber Band/DSP-library import anywhere;
no audio bytes committed anywhere in `tools/p0m3/transition_policy`.

## Scope / immutability

- `policy/compatibility.py`, `policy/eligibility.py`, `policy/metrics.py`,
  `policy/ranking.py`, `policy/policies.py`: **byte-identical** to starting
  HEAD (confirmed via `git diff` — zero lines changed).
- `tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py`:
  **untouched** (not in this session's diff at all).
- No RM IDs, no owner-private timestamps, no environment-local paths
  anywhere in `tools/p0m3/transition_policy/` (this repair is entirely
  synthetic/generic).
- No audio, no Signalsmith, no Rubber Band, no owner listening pack, no P1
  work, no `main` merge.

## Files

- `docs/research/P0-M3-R3-ALIGNMENT-ANCHOR-CONTRACT.md` (this document)
- `tools/p0m3/transition_policy/policy/contract.py`
- `tools/p0m3/transition_policy/policy/boundary.py`
- `tools/p0m3/transition_policy/fixtures/transition_fixtures.json` (TX-08 added)
- `tools/p0m3/transition_policy/fixtures/manifest.json`
- `tools/p0m3/transition_policy/README.md`
- `tools/p0m3/transition_policy/run_benchmark.py`
- `tools/p0m3/transition_policy/verify.py`
- `tools/p0m3/transition_policy/results/boundary_planning.json`,
  `results/SUMMARY.md` (regenerated)

## PM review request

Please independently verify:

1. Run `python tools/p0m3/transition_policy/run_benchmark.py` and
   `python tools/p0m3/transition_policy/verify.py` and confirm `RESULT:
   ALL ASSERTIONS PASS` (179/179).
2. Open `results/boundary_planning.json`'s `TX-08` entry and confirm
   `next_track_entry_window_ms == {"t_start_ms": 0, "t_end_ms": 0}` while
   `incoming_beat_alignment_target_ms == incoming_downbeat_alignment_target_ms
   == 8000` and `FULL_DJ_BLEND` is in `allowed_transition_class_set`.
3. Confirm `git diff` shows zero changes to `policy/compatibility.py`,
   `policy/eligibility.py`, `policy/metrics.py`, `policy/ranking.py`,
   `policy/policies.py`, and
   `tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py`.
4. Confirm no RM ID, owner-private timestamp, or environment-local path
   appears anywhere in the diff.

## Result

**`ALIGNMENT_ANCHOR_CONTRACT_SEPARATED`**

## Next step

The only planned engineering step after PM acceptance is the **FINAL
REAL-CORPUS REPLAY**. It was not performed in this session.
