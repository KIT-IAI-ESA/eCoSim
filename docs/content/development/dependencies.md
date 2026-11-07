# Dependencies

## Add a dependency

- add it to the `pyproject.toml` of the subproject that imports it, not to the root
    - runtime dependencies go into `[project] dependencies`, test-only ones into the `dev` extra
    - the root `pyproject.toml` only holds the development tooling (`pre-commit`, `mypy`, `pytest`, `ruff`)
- **either** sync that subproject: `cd ecosim-server && uv sync --extra dev`
- **or** sync all of them from the root: `python dev/sync_projects.py`, or the PyCharm run config `sync projects`
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

mypy runs strict, so a library without type hints fails with `import-not-found`. Add an override to
the subproject's `[tool.mypy]` instead of loosening the settings:

```toml
[[tool.mypy.overrides]]
module = ["fmpy", "fmpy.*"]
ignore_missing_imports = true
```

- a subproject whose `mypy_path` includes another one needs that one's overrides too
- add the override to the root `mypy.ini` as well, which the IDE uses

## Update the pre-commit hooks

`uv run pre-commit autoupdate` rewrites the versions in `.pre-commit-config.yaml`. It is a deliberate
step for maintainers, `dev/init_dev.py` does not run it:

- run it in the repository root, then `uv run pre-commit run --all-files`, because a new hook version
  may rewrite or reject files
- commit the result as its own change
