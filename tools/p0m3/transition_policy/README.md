# P0-M3-R2 -- Apple-like Near-End Transition Planner + Compatibility Gate

Disposable, research-only prototype for GitHub Issue #6 (redesigned per the
"PM PRODUCT DIRECTION UPDATE -- APPLE-LIKE NEAR-END LISTENING TARGET"
comment, which supersedes the prior repair comment on the same issue).
Answers **WHEN should AutoMix leave the current track and WHICH transition
class is appropriate**, not how to DSP-mix it. No audio is processed or
committed; no Signalsmith Stretch / Rubber Band / production engine code
exists here.

## Layout

```
fixtures/fixtures.json       14 timing/preservation fixtures (letters A-N), metadata-only
fixtures/pair_fixtures.json  5 pair-compatibility fixtures (letters G-K), metadata-only
fixtures/manifest.json       index + spec-letter coverage map + ground-truth-isolation note
policy/metrics.py            effective_content_end_ms / transition_onset / preservation-ratio model
policy/compatibility.py      pair-level mixability gate (genre/tempo/beat/harmonic/energy/vocal/...)
policy/ranking.py            deterministic, order-invariant ranking among eligible near-end candidates
policy/eligibility.py        near-end eligibility model (the SEAMLESS_FULL_TRACK_DEFAULT engine)
policy/policies.py           7 policy candidates (4 baselines + recommended engine + 2 research controls)
policy/contract.py           P0-M3-R3 planner output contract (PlannerDecision)
run_benchmark.py             runs the full matrix, writes results/*.json + SUMMARY.md
verify.py                    independent stop-condition-mapped assertion suite (66 checks)
results/                     generated (committed) output
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
- **Ranked, not first-eligible.** `decide()` (the canonical full-track
  planner) evaluates every non-end candidate, ranks all eligible ones via
  `policy/ranking.py`'s documented lexicographic tuple, and is provably
  invariant to candidate-array order (`results/order_invariance.json`).
  `decide_at_time()` remains a separate TIME-LOCAL query primitive (cannot
  see future candidates) and is never presented as equivalent.
- **Pair compatibility is a separate gate from timing.** `policy/compatibility.py`
  never influences WHEN to exit, only WHICH transition class is allowed once a
  timing decision is made (`downgrade_transition_class_set`). `FULL_DJ_BLEND`
  is withheld whenever no `pair` is supplied to `decide()` at all.
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
