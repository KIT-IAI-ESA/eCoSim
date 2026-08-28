---
name: agent-todo
description: Maintain agent-todo.md, the shared task log at the repository root. Use when starting a multi-step task, when a step completes, or when something worth fixing is noticed but deliberately left alone.
---

# agent-todo.md

`agent-todo.md` at the repository root is the durable task log, shared across agents and
sessions. It survives context loss — treat it as the record, not as a scratchpad.

## Shape

```markdown
- [ ] short statement of the problem, in the words of whoever reported it
  - [ ] 1. what was actually wrong, once understood
  - [ ] 2. the change that addresses it
  - [ ] 3. run the tests of every touched package and pre-commit
```

Rules that keep it readable:

- The top-level entry states the **problem**, not the solution. It is written before the
  cause is known and stays as it was.
- Sub-steps are numbered and describe findings as much as actions — the second step of an
  entry is often "the real cause was X", which is the most valuable line in the file later.
- Tick a box only after verification, never on intent.
- The last step of a task is the verification step.
- Do not invent tasks. Only what was asked, plus what turned out to be necessary.
- Completed entries stay in the file as history. Do not prune them.

## Findings

Below the tasks there is a findings section for things noticed in passing and deliberately
**not** fixed:

```markdown
Findings from the repository fixture task (not fixed, decide if they are worth a task):
- the database returns UTC aware timestamps, the file repository keeps naive ones, so
  `SimulationConfig.date_to_step` is off by the local UTC offset for database entries.
```

Use it instead of either silently widening the task or silently dropping the observation.
Each finding names what is wrong, where, and when it can actually be hit. Findings become
tasks only when the user says so.

## Working with it

At the start of a task, read the file — an open entry may already describe what you are
about to do. At the end, make sure the file reflects reality, including steps that were
skipped and why.
