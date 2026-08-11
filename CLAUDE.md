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

For this project, **Claude Desktop → Code tab/workspace is an approved Claude execution surface**. The embedded Code runtime may identify itself as `Claude Code`, `Claude Code CLI`, or an Agent-SDK/Code runtime; that self-identification does not mean the user launched a forbidden standalone CLI session. Follow the visible Claude Desktop model/effort selection plus the active task contract.

Do not block solely because the embedded Desktop Code runtime calls itself Claude Code. Block only when the requested model/effort cannot actually be selected/verified, or another explicit stop condition applies.

Standalone `claude` terminal/CLI sessions outside Claude Desktop, Cowork/delegated agents, unapproved sub-agents, and silent fallback remain forbidden unless the active task explicitly authorizes them.

## Handoff

A task is not complete until its explicit `HANDOFF TO PM` contract is satisfied.