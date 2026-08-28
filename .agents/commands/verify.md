---
description: Run the full verification gate on the current changes
argument-hint: "[subproject ...]"
---

Verify the current changes using the `verify-changes` skill.

Scope: $ARGUMENTS

If no subproject is given, derive the scope from `git status --short` and
`git diff --name-only HEAD`.

Run, in this order, and stop to report as soon as something fails:

1. `pre-commit` on the changed files — remember that the rewriting hooks need a second run
2. `python dev/run_mypy.py <subproject>` for each touched subproject
3. `uv run pytest` inside each touched subproject
4. `uv run pytest integration_tests/server_client/test_three_client_server.py` in `integration-tests`

Report exactly what ran and what it said, quoting real output for anything that failed. Do
not commit.
