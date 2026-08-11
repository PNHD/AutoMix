# Claude Router — AutoMix

`AGENTS.md` is the canonical repository execution policy. Read it before every task and do not override it from this file.

## Required project skills

Before executing a task, read:

- `.agents/skills/automix-task-contract/SKILL.md`

For research / reverse-engineering / API / DSP feasibility tasks, also read:

- `.agents/skills/automix-forensic-research/SKILL.md`

For implementation review / milestone acceptance tasks, also read:

- `.agents/skills/automix-code-review/SKILL.md`

## Model policy

Use the exact execution profile written in the active task prompt/GitHub issue.

Do not infer permission to change model, effort, Extended Thinking, Dynamic Workflows, or sub-agent settings from any skill or general Claude capability.

If the requested model/effort cannot be selected or verified, follow the fallback/blocking rule in the active task rather than silently substituting another model.

## Handoff

A task is not complete until its explicit `HANDOFF TO PM` contract is satisfied.
