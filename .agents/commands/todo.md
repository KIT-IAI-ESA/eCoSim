---
description: Bring agent-todo.md in line with the actual state of the work
---

Reconcile `agent-todo.md` with reality, following the `agent-todo` skill.

1. Read `agent-todo.md`.
2. Compare its open entries against the working tree (`git status --short`, `git diff`) and
   against what this session actually did.
3. Tick only the steps that are verified — a step whose verification has not run stays open.
4. Add sub-steps for work that turned out to be necessary but was not planned, phrased as
   findings where that is what they are.
5. Move anything noticed but deliberately not fixed into the findings section.

Do not invent tasks, do not prune completed history, and report which entries you changed.
