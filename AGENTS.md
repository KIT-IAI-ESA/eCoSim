# AGENTS.md

Instructions for AI agents working in the eCoSim monorepo. This file is the entry point;
the content lives in `.agents/` so that every agent tool reads the same source.

## Read first

- `.agents/guidelines/general.md` — how to communicate and manage tasks
- `.agents/guidelines/python-coding.md` — the coding rules
- `.agents/guidelines/repository.md` — **how this monorepo actually works**

## Hard rules

- **Never commit or push unless explicitly asked.**
- Every subproject has its own `.venv`: `cd ecosim-server && uv run pytest`. Plain `pytest`
  from the root does not work; `python dev/run_tests.py` runs them all.
- Type hints are mandatory (`mypy` runs with `disallow_untyped_defs`).
- Practise TDD: write the test first.
- Methods stay ≤ 10 lines, classes ≤ 150, files ≤ 150.
- Run `pre-commit` after finishing a task, and report the real result.
- Keep `agent-todo.md` up to date.

## Procedures

Step-by-step procedures for recurring work are in `.agents/skills/<name>/SKILL.md`. Read the
matching one *before* running commands — several encode pitfalls that cost hours otherwise.

| Skill | Use it when |
|---|---|
| `orientation` | you need the map of the codebase |
| `run-tests` | running or verifying tests |
| `verify-changes` | finishing a change; deciding whether work is done |
| `docker-images` | building images or running `dev/docker/example` |
| `add-dependency` | adding, upgrading or removing a dependency |
| `new-subproject` | creating a new `ecosim-*` package |
| `agent-todo` | starting a multi-step task, or noticing something out of scope |

`.agents/commands/` holds the explicit commands (`/verify`, `/todo`).

See `.agents/README.md` for how the setup is wired into the individual tools.
