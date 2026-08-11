# Gemini Router — AutoMix

`AGENTS.md` is the canonical repository execution policy. Read it before every task and do not override it from this file.

## Required project skills

Before executing a task, read:

- `.agents/skills/automix-task-contract/SKILL.md`

For research / source archaeology / API / DSP feasibility tasks, also read:

- `.agents/skills/automix-forensic-research/SKILL.md`

For implementation review / milestone acceptance tasks, also read:

- `.agents/skills/automix-code-review/SKILL.md`

## Model policy

Use the exact execution agent/model/effort profile specified by the active task. Do not silently replace the requested model, reasoning effort, delegation policy, or fallback policy.

## Handoff

A task is not complete until its explicit `HANDOFF TO PM` contract is satisfied.
