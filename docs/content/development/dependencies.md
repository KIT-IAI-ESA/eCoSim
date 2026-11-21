# Dependencies

## Add a dependency

- add it to the `pyproject.toml` of the subproject that imports it, not to the root
    - runtime dependencies go into `[project] dependencies`, test-only ones into the `dev` extra
    - in `ecosim-test-common`, fmpy is an extra, so the subprojects without FMUs don't install it; the ones with FMUs
      already depend on fmpy and keep the plain pin `ecosim-test-common==0.14.0`
    - the root `pyproject.toml` only holds the development tooling (`pre-commit`, `mypy`, `pytest`, `ruff`)
- **either** sync that subproject: `cd ecosim-server && uv sync --extra dev`
- **or** sync all of them from the root: `python dev/sync_projects.py`
    - it recreates every `.venv` (`uv venv --clear`) first, so prefer the single sync while you work
- commit the subproject's `uv.lock` together with its `pyproject.toml`

## Another eCoSim package

The subprojects use each other from the working tree:

```toml
[project]
dependencies = ["ecosim-common==0.14.0"]

[tool.uv.sources]
ecosim-common = { path = "../ecosim-common", editable = true }
```

- the version is pinned exactly, so a version bump changes every `pyproject.toml` at once
    - `python dev/bump_version.py 0.15.0` sets the version and every pin, then refreshes each `uv.lock`
- for mypy, add the package to `mypy_path` in `[tool.mypy]`: `mypy_path = ["../ecosim-common"]`

## Libraries without type hints

mypy uses the settings in each subproject's `[tool.mypy]` (`check_untyped_defs` and
`disallow_untyped_defs`), not `--strict`. Only the scripts in `dev/` are checked with `--strict`.
A library without type hints fails with `import-untyped`, or with `import-not-found` if it is not
installed. Add an override to the subproject's `[tool.mypy]` instead of loosening the settings:

```toml
[[tool.mypy.overrides]]
module = ["fmpy", "fmpy.*"]
ignore_missing_imports = true
```

- a subproject whose `mypy_path` includes another one needs that one's overrides too
- add the override to the root `mypy.ini` as well, which the IDE uses

## Updates from Dependabot

Dependabot opens one grouped pull request a week for the GitHub Actions and one a month for the packages of
the docs site in `docs/`, as set in `.github/dependabot.yml`.
The Python packages are updated by hand for now: the same exact pins appear in several subprojects, and
Dependabot updates one directory at a time, so its updates can't be resolved.

## Update the pre-commit hooks

`uv run pre-commit autoupdate` rewrites the versions in `.pre-commit-config.yaml`. It is a deliberate
step for maintainers, `dev/init_dev.py` does not run it:

- run it in the repository root, then `uv run pre-commit run --all-files`, because a new hook version
  may rewrite or reject files
- commit the result as its own change
