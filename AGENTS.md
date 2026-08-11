# AutoMix Agent Execution Contract

## Mission

Build a provider-independent AutoMix system whose transition quality is evaluated against strong commercial references, while respecting platform terms, DRM boundaries, copyright, and public-repository safety.

## Current phase

**P0 — Feasibility & Reference Baseline**

No production app implementation is accepted during P0 unless a task explicitly authorizes a disposable experiment.

## Non-negotiable rules

1. Evidence before conclusions. Cite exact repository paths, symbols, commits, official documentation, benchmark outputs, or reproducible commands.
2. Do not claim PASS because code compiles or a transition sounds subjectively acceptable.
3. Do not bypass DRM, extract protected provider audio, steal session credentials, or commit cookies/tokens/private account material.
4. Do not commit copyrighted commercial audio test files. Use synthetic, CC-licensed, public-domain, or owner-supplied local fixtures excluded from git.
5. Provider integrations must be isolated behind adapters. The AutoMix analysis/planning/DSP core must not depend on Spotify, Apple Music, YouTube Music, or another provider.
6. Treat public API policy and licensed-partner capabilities as different things. Do not infer public access from capabilities available only to approved partners.
7. If a required capability is blocked by API policy or DRM, document the blocker and continue with the nearest legal test surface instead of bypassing it.
8. No merge to `main` unless explicitly requested by the project owner/PM.

## Quality terminology

- **Crossfade**: volume overlap only.
- **DJ-style crossfade**: crossfade plus filters/EQ and possibly tempo/key adjustment.
- **Beat-aware**: uses explicit beat timestamps/grid.
- **Downbeat-aware**: aligns bar starts/downbeats, not only BPM.
- **Phrase-aware**: selects transition entry/exit using musical phrase boundaries.
- **Section-aware**: understands intro/verse/chorus/outro or equivalent structural sections.
- **AutoMix PASS**: must satisfy the acceptance criteria of the active task; BPM/key matching alone is insufficient.

## Reporting format

Every task report must include:

1. Result: PASS / PARTIAL / BLOCKED / FAIL
2. Exact commit/ref inspected
3. Evidence
4. Findings
5. Unknowns
6. Risks
7. Recommended next action

Do not hide failed experiments or unresolved uncertainty.
