# P0-M3-R2 -- Apple-like Near-End Transition Planner + Compatibility Gate

Disposable, research-only prototype for GitHub Issue #6, now on its second
repair pass ("PM REVIEW #2 -- FINAL PRE-DSP CONTRACT REPAIR REQUIRED",
following the "PM PRODUCT DIRECTION UPDATE -- APPLE-LIKE NEAR-END LISTENING
TARGET" comment that preceded it). Answers **WHEN should AutoMix leave the
current track, WHERE should it enter the next track, and WHICH transition
class is appropriate for that complete boundary** -- not how to DSP-mix it.
No audio is processed or committed; no Signalsmith Stretch / Rubber Band /
production engine code exists here.

## Layout

```
fixtures/fixtures.json            14 timing/preservation fixtures (letters A-N), single-track/legacy planner, metadata-only
fixtures/pair_fixtures.json       10 pair-compatibility fixtures (letters G-K + R4 mutation pairs PAIR-06..10), metadata-only
fixtures/transition_fixtures.json 5 COMPLETE boundary-planning fixtures TX-01..05 (outgoing exit x incoming entry x pair), metadata-only
fixtures/manifest.json            index + spec-letter coverage map + ground-truth-isolation note
policy/metrics.py                 effective_content_end_ms / transition_onset / preservation-ratio model
policy/compatibility.py           pair-level mixability gate (genre/tempo/beat/harmonic/energy/vocal/...); R4 hard-gates structure+texture+harmonic
policy/ranking.py                 deterministic, order-invariant ranking (single-candidate AND full boundary-plan variants)
policy/eligibility.py             near-end eligibility model (the SEAMLESS_FULL_TRACK_DEFAULT engine) -- SAFE-exit filter only, never pair-aware
policy/boundary.py                PM REVIEW #2 R1/R2: ranks COMPLETE (exit, entry, pair-at-that-boundary) plans; plans real incoming entries
policy/policies.py                7 policy candidates (4 baselines + recommended engine + 2 research controls) for the legacy single-track planner
policy/contract.py                P0-M3-R3 planner output contract (PlannerDecision) -- both-sides alignment, unambiguous tempo/pitch fields
run_benchmark.py                  runs the full matrix, writes results/*.json + SUMMARY.md
verify.py                         independent stop-condition-mapped assertion suite (111 checks)
results/                          generated (committed) output
```

## Run

```bash
python run_benchmark.py
python verify.py
```

Both are stdlib-only (no `pip install` required) and fully deterministic --
re-running produces byte-identical `results/*.json` (only `results/SUMMARY.md`'s
prose is templated from the same numbers; `results/order_invariance.json`'s
shuffle uses a fixed seed).

## Design notes

- **Preservation, not fraction-consumed.** `policy/metrics.py` separates
  `transition_onset_ms` (when incoming audio starts) from
  `outgoing_content_preservation_ratio` (when the outgoing track's meaningful
  content actually stops being audible, accounting for overlap). A transition
  can start tens of seconds before a song's natural end and still preserve
  ~100% of its content if the overlap covers the remainder.
- **Boundary plans, not exit-only ranking (PM REVIEW #2 R1).**
  `policy/boundary.py`'s `plan_transition_boundary()` is the canonical
  planner for any fixture that models an incoming track. It (1) filters
  outgoing candidates to the SAFE set using the existing eligibility guards
  -- pair compatibility is never consulted here, so it can never authorize
  an early exit -- then (2) evaluates every (safe exit x entry) combination's
  pair compatibility AT that specific boundary and ranks all eligible
  combinations via `policy/ranking.rank_boundary_plans`. The winner is the
  best COMPLETE boundary, not merely the best outgoing exit with pair
  compatibility bolted on afterward. `policy/policies.py`'s `decide()`
  remains the single-track/legacy planner for fixtures with no incoming
  track modeled (letters A-N); its ranking key also now carries a
  pair-compatibility tier for architectural consistency, though a single
  global `pair` cannot differentiate between same-track candidates the way
  per-boundary compatibility can.
- **Ranked, not first-eligible.** Every ranked planner (single-track or
  boundary) evaluates every candidate/combination, ranks all eligible ones
  via `policy/ranking.py`'s documented lexicographic tuple, and is provably
  invariant to array order on every axis involved
  (`results/order_invariance.json`, `results/boundary_planning.json`'s
  `tx01_order_invariance`). `decide_at_time()` remains a separate TIME-LOCAL
  query primitive (cannot see future candidates) and is never presented as
  equivalent.
- **Real incoming-entry planning, not a `{0,0}` placeholder (R2).**
  `policy/boundary.py` evaluates every incoming entry candidate: `t_ms == 0`
  is always valid; a later point is valid only if it's an authored
  non-musical silence skip or carries explicit phrase/cue evidence --
  otherwise it's rejected as silently removing meaningful intro content.
- **Real narrow onset windows, never onset..content_end.**
  `transition_onset_window_ms` / the incoming entry window are always exact
  cue timestamps (`t_start_ms == t_end_ms`) unless a candidate carries an
  explicit authored `onset_window_ms` region.
- **Both sides of alignment are identified (never one timestamp reused).**
  `outgoing_beat_alignment_target_ms` and `incoming_beat_alignment_target_ms`
  (and the downbeat equivalents) are always distinct fields; a boundary
  decision never claims to specify the incoming side using the outgoing
  timestamp.
- **Unambiguous tempo/pitch contract (R3).** `required_tempo_ratio` (a real
  playback-rate ratio) is a distinct field from
  `permitted_tempo_ratio_max_deviation` (a deviation ceiling, currently
  0.12) -- the old `permitted_tempo_ratio` field name no longer exists.
  Pitch is `required_pitch_shift_semitones` +
  `permitted_pitch_shift_semitones_min/max`, never a bare unitless integer.
- **Strict FULL_DJ_BLEND hard gate (R4).** `policy/compatibility.py`
  requires `structure_compatibility` and `intro_outro_texture_compatible`
  to be KNOWN and COMPATIBLE (not merely absent/UNKNOWN) before
  `FULL_DJ_BLEND` is ever offered. `harmonic_relationship` UNKNOWN
  downgrades FULL_DJ_BLEND unless an explicit, narrow
  `harmonic_not_load_bearing_reason` exception is supplied (PAIR-08 vs
  PAIR-09). `harmonic_relationship == INCOMPATIBLE` always rejects
  FULL_DJ_BLEND regardless of any exception (PAIR-10). Energy continuity
  remains a ranking/preference signal AFTER these hard gates, never a hard
  rejection on its own.
- `SEAMLESS_FULL_TRACK_DEFAULT` is the only current product-default policy.
  `BALANCED_MIX_RESEARCH_CONTROL` and `EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL`
  are research/negative controls only -- independently computed rows that
  never influence the default engine's own decision path.
- Ground-truth-only fixture fields (`is_premature_trap`,
  `is_vocal_collision_trap`, `is_valid_natural_exit`,
  `is_preferred_earliest_valid_exit`, `highlight_eligible`,
  `expected_overall_eligible`) exist only for `run_benchmark.py`'s scoring
  code. `verify.py` check 0 statically proves (via `ast`, not string-grep)
  that no `policy/*.py` module ever reads them.
- No eligibility/decision function anywhere in `policy/` accepts a "next
  track quality"/queue argument for TIMING purposes -- a structural (not
  just behavioral) enforcement that queue order never grants permission to
  exit the current track early.

See `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` for the full
design rationale, the Apple-like public-evidence-vs-project-inference
boundary, and the complete fixture/metric/AC matrix.
