# Scenario E -- Pitch-Shift Stress: `NOT_TESTED_NO_VALID_PLANNER_INPUT`

Per Issue #7: *"E -- OPTIONAL PITCH-SHIFT STRESS FIXTURE. Only if a
deterministic, legally safe harmonic fixture can justify a known nonzero
semitone correction without changing R2 policy semantics. If not justified,
do NOT fabricate it. Report `NOT_TESTED_NO_VALID_PLANNER_INPUT`."*

## Evidence

The accepted R2 planner contract
(`tools/p0m3/transition_policy/policy/boundary.py`,
`tools/p0m3/transition_policy/policy/compatibility.py`, PM REVIEW #3 §24
"R7 -- structured, machine-verifiable harmonic exception") computes
`required_pitch_shift_semitones` in exactly two live code paths, both in
`policy/boundary.py`'s `plan_transition_boundary()`:

```python
if compat.harmonic_compatibility == "COMPATIBLE":
    required_pitch = 0
    pitch_range = (-3, 3)
elif compat.harmonic_exception_applied:
    required_pitch = 0
    pitch_range = (0, 0)
else:
    required_pitch = None
    pitch_range = (None, None)
```

(`policy/contract.py`'s legacy single-track `build_transition_decision`
mirrors the identical two branches.)

**`required_pitch_shift_semitones` is literally `0` or `None` in every
reachable code path of the accepted R2 planner.** There is no branch,
under any fixture input, that can make R2 emit a nonzero
`required_pitch_shift_semitones`. This project does not compute a real
semitone correction without actual key detection (per
`P0-M3-R2-TRANSITION-POLICY-PLANNER.md` §19: *"This project does not
compute a real semitone value without actual key detection, and does not
fabricate one"*) -- so there is no fixture input, however constructed,
that could legitimately drive a nonzero pitch-shift render through the
accepted planner without either (a) inventing a new planner code path
not accepted by PM REVIEW #3 (out of scope, and would itself be "silently
selecting a different pitch correction," which Issue #7 explicitly
forbids), or (b) hand-fabricating a `PlannerDecision` value the planner
itself would never produce (explicitly forbidden: "If not justified, do
NOT fabricate it").

## Conclusion

`NOT_TESTED_NO_VALID_PLANNER_INPUT`

Verified by direct inspection of `policy/boundary.py` and
`policy/compatibility.py` at the accepted P0-M3-R2 HEAD
(`4e99fec5d34a34cc920d918dc166e452ccdd792a`) -- reproducible via:

```
grep -n "required_pitch_shift_semitones" tools/p0m3/transition_policy/policy/boundary.py tools/p0m3/transition_policy/policy/contract.py
```

Every assignment site sets it to `0` or `None`.

This is a `FACT` (direct code inspection of the accepted, pinned planner),
not an inference about hypothetical future R2 versions. If a later R2 pass
adds real key-detection-driven pitch correction, this scenario should be
revisited then, using whatever new fixture shape that pass introduces --
not fabricated ahead of that work.
