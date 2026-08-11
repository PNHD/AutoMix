# AutoMix Agent Skills Audit

Status date: 2026-08-11

This file records agent-skill and agent-instruction sources reviewed for AutoMix. It is intentionally stricter than a normal skills registry because AutoMix is a public repository and task prompts enforce explicit model/effort and no-uncontrolled-delegation rules.

## Decision policy

A third-party skill is not approved merely because it appears on skills.sh, has high install counts, or has a relevant title.

Before adoption, inspect:

1. actual `SKILL.md` contents and any referenced scripts/resources;
2. upstream repository and exact commit;
3. license;
4. secret/network/shell behavior;
5. delegation/sub-agent/model-fallback instructions;
6. whether the content is actually relevant to AutoMix rather than generically named;
7. whether vendoring is necessary at the current phase.

No `@latest`/unpinned remote skill installer is permitted in AutoMix CI.

## Skill format / discovery baseline

AutoMix uses the open Agent Skills layout: one directory per skill with a required `SKILL.md` containing YAML `name` and `description` plus Markdown instructions.

Canonical project path used here:

`.agents/skills/<skill-name>/SKILL.md`

This path is supported by current GitHub Copilot project skills and current Android Studio Agent Mode. AutoMix therefore avoids duplicating the same skill into vendor-specific directories unless a future tool proves it cannot read `.agents/skills`.

References:

- https://agentskills.io/specification
- https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- https://developer.android.com/studio/gemini/skills
- https://www.skills.sh/docs

## Installed AutoMix-local skills

These are project-owned skills, not copied third-party packages.

### `automix-task-contract`

Path: `.agents/skills/automix-task-contract/SKILL.md`

Purpose:

- enforce exact agent/model/effort selection;
- enforce Extended Thinking / dynamic workflow / sub-agent policy;
- prohibit silent model fallback;
- turn task AC into an execution checklist;
- require evidence-gated PASS;
- require a structured `HANDOFF TO PM`.

Status: `INSTALLED_REQUIRED`

### `automix-forensic-research`

Path: `.agents/skills/automix-forensic-research/SKILL.md`

Purpose:

- pin repository revisions and submodules;
- trace control/data flow end-to-end;
- require repository-wide negative proof;
- separate public API from partner-only capabilities;
- preserve DRM/provider boundaries;
- distinguish BPM-aware, beat-aware, downbeat-aware, phrase-aware and section-aware behavior.

Status: `INSTALLED_REQUIRED_FOR_RESEARCH`

### `automix-code-review`

Path: `.agents/skills/automix-code-review/SKILL.md`

Purpose:

- review actual diffs against active task AC;
- check audio/DSP correctness and real-time safety;
- check provider isolation, secrets, lifecycle/race behavior and platform divergence;
- return `ACCEPT`, `REQUEST_CHANGES`, or `INSUFFICIENT_EVIDENCE`.

Status: `INSTALLED_FOR_IMPLEMENTATION_AND_REVIEW`

## External skill sources reviewed

### Chris Banes — `chrisbanes/skills`

Repository: https://github.com/chrisbanes/skills

Pinned review commit: `e04a16e079c578b489d201cbed8a30396e2d67b0`

License: Apache-2.0.

Relevant current skills:

- `skills/kotlin-api-design/SKILL.md`
  - semantic platform boundaries;
  - narrow `expect/actual` or interfaces;
  - keep native SDK details at platform leaves.
- `skills/kotlin-concurrency-and-flow/SKILL.md`
  - structured coroutine ownership;
  - cancellation/replay/state/event semantics.

Important audit result: older registry references to a standalone `kotlin-multiplatform-expect-actual` skill are stale. The upstream repository made a breaking taxonomy change and folded that material into `kotlin-api-design`.

Decision: `APPROVED_DEFERRED`.

Reason: very relevant once Kotlin Multiplatform application/core code exists, but installing now would add guidance for a stack that P0 has not yet selected. Re-evaluate/pin again when entering KMP implementation.

### Google / Android — `android/skills`

Repository: https://github.com/android/skills

Pinned review commit: `1e5e7ae6138bebd0835d0d5854b0b9adfeed3181`

Relevant reviewed skill:

- `testing/testing-setup/SKILL.md`
  - current skill analyzes native Android testing stack and can install test infrastructure.

Decision: `APPROVED_DEFERRED`.

Reason: official/current source, but it may choose DI/testing defaults when none exist. Do not run it before the Android module and architecture are intentionally selected. Install only in an Android-specific task with exact scope.

No dedicated current Media3/ExoPlayer music-mixing skill was found in this repository during this audit.

### Block — `block/agent-skills`

Repository: https://github.com/block/agent-skills

Pinned review commit: `329a55d1500748a0a48d64629757cbe2622e34bf`

Relevant reviewed skill:

- `code-review/SKILL.md`

Decision: `REFERENCE_ONLY`.

Reason: clean, simple checklist, but too generic for AutoMix. AutoMix now has a stricter project-owned code-review skill covering real-time audio, DSP semantics, provider isolation and PM evidence gates.

The repository's generic `testing-strategy` is web/npm oriented and uses generic coverage guidance, so it is not adopted as the AutoMix testing contract.

### OpenAI skills catalog

Repository reviewed: https://github.com/openai/skills

Decision: `DO_NOT_INSTALL_FROM_DEPRECATED_CATALOG`.

Reason: the repository currently identifies itself as deprecated and points users to the newer OpenAI Plugins workflow. AutoMix keeps its portable project skills in `.agents/skills`; if a Codex-only plugin becomes necessary later, evaluate the current official OpenAI plugin guidance at that time rather than installing from the deprecated catalog.

### skills.sh

Registry/docs: https://www.skills.sh/docs

Decision: `DISCOVERY_SOURCE_NOT_TRUST_SOURCE`.

Reason: useful for discovering candidates, but skills.sh itself states that it cannot guarantee the quality or security of every listed skill and recommends review before installation. AutoMix therefore resolves a listing back to the source repository and pins/audits the actual content before adoption.

## Rejected / not installed candidates

### Skills that mandate sub-agents or parallel delegation

Decision: `REJECT_POLICY_CONFLICT` unless locally rewritten and explicitly approved for a task.

Reason: AutoMix tasks default to sub-agents OFF and forbid silent delegation/model inheritance. A skill cannot override the active task's execution profile.

Examples encountered during discovery include code-review workflows whose instructions explicitly dispatch one or multiple review sub-agents. Their general idea may be useful, but their execution model is incompatible with the project contract.

### Generic browser/Tone.js FFT audio-analysis skills

Decision: `REJECT_WRONG_ABSTRACTION`.

Reason: FFT visualization or simple frequency-bin analysis is not a substitute for beat timestamps, downbeats, bars, phrase/section boundaries, vocal activity, energy/loudness contours, or transition planning.

### Skills with uncertain or failing security/audit signals

Decision: `REJECT_OR_DEFER`.

Do not install until source, scripts, network behavior, license and current audit status are independently reviewed.

## Future installation triggers

Install/adapt additional third-party skills only at these gates:

- **KMP architecture selected:** reconsider Chris Banes `kotlin-api-design` and `kotlin-concurrency-and-flow` at a newly pinned commit.
- **Android module exists:** reconsider selected official `android/skills` entries, task-by-task.
- **UI phase begins:** research current mobile/Compose/SwiftUI design and accessibility skills, preferring platform-vendor guidance.
- **Native DSP dependencies land:** add a dependency/license/security review skill or plugin only after checking that it does not alter the model/delegation policy.
- **CI/release phase begins:** evaluate current platform-specific build/sign/release skills with strict secret-handling review.

## Update rule

Any skill update requires:

1. new upstream commit pin;
2. diff review from the currently approved revision;
3. license re-check;
4. behavior/policy re-check;
5. updated decision in this document.

No silent skill upgrades.
