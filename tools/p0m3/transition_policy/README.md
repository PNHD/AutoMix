# P0-M3-R2 -- Transition-Policy / Song-Preservation Benchmark

Disposable, research-only prototype for GitHub Issue #6. Answers **WHEN
should AutoMix leave the current track**, not how to DSP-mix it. No audio
is processed or committed; no Signalsmith Stretch / Rubber Band / production
engine code exists here (AC16/AC17).

## Layout

```
fixtures/fixtures.json     10 adversarial fixtures (Task D), metadata-only
fixtures/manifest.json     index + Task D coverage map + ground-truth-isolation note
policy/eligibility.py      Task B eligibility model (the recommended STRUCTURE_AWARE_PRESERVATION policy)
policy/policies.py         5 policy candidates (Task E) + decide()/decide_at_time()
policy/contract.py         Task G planner output contract (PlannerDecision)
run_benchmark.py           runs the full matrix, writes results/*.json + SUMMARY.md
verify.py                  independent AC-mapped assertion suite
results/                   generated (committed) output -- decision_traces.json, metrics.json,
                            sensitivity_matrix.json, playthrough_demo.json, SUMMARY.md
```

## Run

```bash
python run_benchmark.py
python verify.py
```

Both are stdlib-only (no `pip install` required) and fully deterministic --
re-running produces byte-identical `results/*.json` (only `results/SUMMARY.md`'s
prose is templated from the same numbers).

## Design notes

- A fixture is a single current track plus a small set of time-ordered
  **candidate exit points**, each carrying explicit structural/confidence/
  vocal-risk features (Task B). The final (`is_end_of_track=true`) candidate
  represents "the track played to its own natural/authored boundary."
- Ground-truth-only fields (`is_premature_trap`, `is_vocal_collision_trap`,
  `is_valid_natural_exit`, `is_preferred_earliest_valid_exit`,
  `highlight_eligible`) exist only for `run_benchmark.py`'s scoring code.
  `verify.py`'s check 0 statically proves (via `ast`, not string-grep, so
  documentation prose is never a false positive) that `policy/eligibility.py`,
  `policy/policies.py`, and `policy/contract.py` never read them.
- `decide_at_time(fixture, policy, intent, evaluation_time_ms)` is the core
  primitive: it only considers candidates up to `evaluation_time_ms`, which
  is what makes `PLAY_THROUGH` ("nothing eligible yet, more track remains")
  meaningfully distinct from `NO_SPECIAL_TRANSITION` ("track reached its
  natural end with nothing eligible selected"). `decide()` is `decide_at_time`
  called at `duration_ms` (the full-track batch decision used for the main
  metrics matrix).
- No eligibility/decision function anywhere in `policy/` accepts a
  "next track" or "queue quality" argument at all -- this is a structural
  (not just behavioral) enforcement of P4/AC11.
