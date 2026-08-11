---
name: automix-task-contract
description: Enforce AutoMix task execution profile, scope, evidence gates, model/effort pinning, and mandatory PM handoff for every repository task.
---

# AutoMix Task Contract

Use this skill at the start and closeout of every AutoMix repository task.

## Start gate

1. Read repository-root `AGENTS.md` and the active GitHub issue/task prompt before doing work.
2. Verify the prompt explicitly pins:
   - execution agent
   - exact model
   - reasoning effort
   - extended-thinking state when applicable
   - dynamic-workflow policy
   - sub-agent policy
   - fallback policy
3. For Claude work, **Claude Desktop → Code tab/workspace is an allowed execution surface**, even if the embedded runtime internally identifies itself as `Claude Code`, `Claude Code CLI`, or an Agent-SDK/Code runtime. Do not confuse that embedded runtime identity with a standalone terminal/CLI session.
4. The exact requested model/effort must still be visibly selected/verified in Claude Desktop. If the model/effort cannot be satisfied, stop with `BLOCKED_MODEL_SELECTION`. A Desktop Code-tab session must NOT block merely because its embedded runtime calls itself Claude Code.
5. Standalone `claude` terminal sessions, standalone Claude Code CLI/Agent SDK outside Claude Desktop, Cowork/delegated agents, dynamic delegation, and unapproved sub-agents remain forbidden unless the active task explicitly authorizes them.
6. Dynamic workflows and sub-agents are OFF unless the task explicitly authorizes them. Authorization must also pin model/effort for any delegated agent.
7. Extract the task's scope, prohibited actions, deliverables, branch, acceptance criteria, and stop conditions into a short execution checklist before editing.
8. Do not widen scope because adjacent work looks useful. Record adjacent work as a recommendation instead.

## Evidence gate

A claim is accepted only when supported by at least one of:

- exact repository path + symbol + pinned commit/ref
- official documentation with version/date when relevant
- reproducible command and captured result
- deterministic test/benchmark output
- CI run/log/artifact ID

Distinguish `FACT`, `INFERENCE`, and `UNKNOWN_NEEDS_PROOF` in research-heavy work.

## Completion gate

Do not report PASS because code compiles, a UI renders, or audio subjectively sounds acceptable. PASS means every task-specific acceptance criterion has independently checkable evidence.

Before closing:

1. Inspect the final diff/commit.
2. Run all task-required validation.
3. Check that no secrets, credentials, cookies, protected media, or owner-private fixtures were committed.
4. Confirm no unauthorized merge to `main` occurred.
5. Produce the mandatory handoff below.

## HANDOFF TO PM

Return:

- `RESULT`: PASS / PARTIAL / BLOCKED / FAIL
- `REPO`
- `BRANCH`
- `HEAD`: exact commit SHA or `NO COMMIT` + reason
- `FILES`: created/modified files
- `VALIDATION`: commands/tests/searches and exact results
- `AC CHECK`: each acceptance criterion with PASS/FAIL + evidence
- `EVIDENCE`: key paths/symbols/logs/CI/artifacts/source refs
- `UNKNOWNS / RISKS`
- `PM REVIEW REQUEST`: exact items the PM should independently inspect next

A bare `done`, generic narrative summary, or unverified claim is not a valid handoff.