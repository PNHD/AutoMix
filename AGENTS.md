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

## Mandatory task execution header

Every task prompt issued by the PM MUST explicitly state all of the following. If any field is missing, the task is not ready to execute.

- **Execution agent:** Codex / Claude / Gemini / other approved agent.
- **Model:** exact model requested by the PM.
- **Reasoning effort:** Low / Medium / High or the platform-equivalent exact setting.
- **Extended thinking:** On / Off when applicable.
- **Dynamic workflows:** default OFF unless the PM explicitly overrides it.
- **Sub-agents:** default OFF. Do not spawn parallel/nested/delegated agents unless the task prompt explicitly authorizes them and pins their model/effort.
- **Fallback policy:** no silent model fallback. If the requested model cannot be selected or verified, report BLOCKED unless the task prompt provides an approved fallback.

For Claude repository work, the default unless a task says otherwise is:

- Parent: Sonnet High
- Extended thinking: ON
- Dynamic workflows: OFF
- Sub-agents: OFF

## Mandatory PM handoff

Every task prompt MUST end with a `HANDOFF TO PM` section that tells the executing agent exactly what to return for review. At minimum require:

1. Result: PASS / PARTIAL / BLOCKED / FAIL.
2. Repository + branch.
3. Exact HEAD commit SHA after the task, or `NO COMMIT` with reason.
4. Files created/modified.
5. Commands/tests run and their exact results.
6. Evidence supporting each acceptance criterion.
7. Unknowns, failures, risks, and any assumptions.
8. Links/IDs for PRs, issues, CI runs, artifacts, logs, or external research used.
9. A concise `PM REVIEW REQUEST` stating exactly what the PM should inspect next.

Do not end with only a prose summary such as “done”. The handoff must be sufficient for the PM to independently verify the work without reconstructing the agent's session.

## External skill / agent-extension supply-chain policy

AutoMix is a public repository. Treat every third-party `SKILL.md`, agent pack, MCP bundle, installer, workflow template, and copied agent instruction as executable supply-chain input even when it contains only prose.

Before adopting one:

1. Inspect the actual source repository and exact skill contents; do not trust the registry title, install count, or summary alone.
2. Prefer first-party/official sources or established maintainers with explicit licenses.
3. Check for instructions that read secrets, upload local files, weaken sandboxing, auto-run shell/network commands, alter Git credentials, or spawn uncontrolled agents.
4. Check behavior against this repository's model/quota policy. Any skill that mandates sub-agents, dynamic delegation, unpinned model fallback, or a forbidden model must be rejected or locally adapted before use.
5. Pin the upstream commit/ref in `docs/research/AGENT-SKILLS-AUDIT.md` before vendoring/adapting.
6. Do not execute `npx skills add ...@latest`, curl-pipe-shell installers, or equivalent unpinned remote installers in CI.
7. Vendored/adapted third-party content must preserve required license/attribution notices.
8. Re-audit before updating a pinned skill. No silent upgrades.

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
