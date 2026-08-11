---
name: automix-code-review
description: Review AutoMix changes against task acceptance criteria, audio/DSP correctness, real-time safety, provider boundaries, secrets, tests, and platform behavior without spawning sub-agents.
---

# AutoMix Code Review

Use after non-trivial implementation changes and before asking the PM to accept a milestone.

## Review target

Start from the active issue/task acceptance criteria, then inspect the actual diff and adjacent call paths. Do not review only filenames or the PR description.

## Priority order

### P0 — correctness/safety blockers

- task behavior is not actually implemented end-to-end
- playback/transition state can corrupt, deadlock, race, leak, or crash
- real-time audio callback performs blocking I/O, unbounded allocation, locks, network work, or other unsafe work
- provider-specific behavior leaks into the analysis/planning/DSP core
- secrets/tokens/cookies/private media are committed or logged
- DRM/provider restrictions are bypassed
- claimed PASS lacks runtime/benchmark evidence required by the task

### P1 — material quality/regression risks

- incorrect tempo/beat/downbeat/phrase semantics
- sign/unit/timebase/sample-rate/channel-layout mistakes
- transition scheduling can drift or double-trigger
- fallback behavior is undefined for missing/low-confidence analysis
- cancellation/lifecycle ownership is unclear
- Android/Desktop/iOS behavior diverges unintentionally
- tests assert implementation details instead of the product contract

### P2 — maintainability/performance

- duplicated DSP/planner logic across providers/platforms
- hidden constants without documented units/rationale
- unnecessary allocations or repeated analysis on hot paths
- public API exposes platform/provider types unnecessarily
- insufficient diagnostics for reproducing audio-quality failures

## Required review evidence

For every blocking finding:

1. cite exact file + symbol/line region;
2. describe the concrete failure mode;
3. state which acceptance criterion or invariant it violates;
4. propose the smallest safe correction;
5. state what test/benchmark would prove the correction.

Do not invent defects. If a suspected problem requires runtime evidence, label it `NEEDS_RUNTIME_PROOF` rather than asserting it as fact.

## Review closeout

Return:

- blocking findings first, highest severity first
- non-blocking risks
- missing tests/evidence
- explicit verdict: `ACCEPT`, `REQUEST_CHANGES`, or `INSUFFICIENT_EVIDENCE`

Then produce the standard `HANDOFF TO PM` from `automix-task-contract`.
