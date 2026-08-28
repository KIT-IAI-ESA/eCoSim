---
name: verify-changes
description: Verify changed files before handing work back - pre-commit, mypy and tests. Use after finishing any code change, and whenever asked whether the work is done, clean or ready to commit.
---

# Verify changes

The gate every change has to pass. Run it from the repository root, in this order — the
cheap checks first, so a formatting failure does not cost a full test run.

## 1. pre-commit on the changed files

```shell
uv run pre-commit run --files $(git diff --name-only HEAD) --show-diff-on-failure
```

For a change that touches many packages, `--all-files` is the honest check, but it runs
`mypy` for all ten subprojects and takes minutes.

**`pre-commit` only sees files git knows about.** A brand new file that is still untracked
is reported as `(no files to check) Skipped` for every hook — which looks like success. Run
`git add` on new files first, and check that the output actually says `Passed` rather than
`Skipped`.

Note also that `dev/` is not covered by any of the `mypy` hooks (they are scoped to
`^ecosim-*/`). Type-check a changed dev script directly:
`uv run mypy --strict --ignore-missing-imports dev/run_tests.py`.

Several hooks **rewrite** files (`trailing-whitespace`, `end-of-file-fixer`,
`add-trailing-comma`, `ruff --fix`, `ruff-format`). A first run that reports `Failed` with
`files were modified by this hook` is normal: inspect the diff it made, then run again. The
run is only clean when a second invocation reports nothing.

## 2. mypy for each touched subproject

`mypy` is configured per subproject and must run inside it. Use the wrapper, which handles
the `VIRTUAL_ENV` unsetting that trips up `uv` otherwise:

```shell
python dev/run_mypy.py ecosim-server
```

The root `mypy.ini` is **only** for the IDE — it is not the config CI uses. Each subproject
has its own `[tool.mypy]`. Type checking is strict (`disallow_untyped_defs`), so every new
function needs annotations, including `-> None`.

## 3. Tests for each touched subproject

```shell
python dev/run_tests.py
```

That covers every subproject except `integration-tests`. To stay quick while iterating,
limit it: `python dev/run_tests.py ecosim-server`. If you touched `ecosim-common`, run
everything — the rest depends on it. See the `run-tests` skill for the details.

## What the hooks will reject

- a Python filename that is not `snake_case`
- a line longer than 150 characters
- a missing trailing comma in a multi-line call or signature
- a missing newline at end of file
- a leftover `breakpoint()` / `pdb` call (`debug-statements`)
- an f-string inside a logging call — ruff `G004`; use `logger.debug("x %s", value)`
- accessing a private member across objects — ruff `SLF001`

## Finishing

- Report what you ran and what it said. Quote the failure, do not summarise it away.
- **Never commit or push unless explicitly asked.** A clean verification is not permission
  to commit.
- If something is still failing and you are out of ideas, say so plainly instead of
  narrowing the check until it passes.
