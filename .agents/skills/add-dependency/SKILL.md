---
name: add-dependency
description: Add, upgrade or remove a Python dependency in one of the subprojects, including the private KIT GitLab package registry. Use when a package needs to be installed or a version changed.
---

# Add a dependency

## The dependency belongs to a subproject, not the root

Edit the `pyproject.toml` of the subproject that imports it — for example
`ecosim-server/pyproject.toml`. The root `pyproject.toml` only carries the development
tooling (`pre-commit`, `mypy`, `pytest`, `ruff`) under the `dev` extra.

Runtime dependencies go into `[project] dependencies`, test-only ones into the `dev` extra
of that same subproject.

## Then sync

Either just that subproject:

```shell
cd ecosim-server && uv sync --extra dev
```

Or everything, from the repository root:

```shell
python dev/sync_projects.py
```

`sync_projects.py` recreates each `.venv` with `uv venv --clear` before syncing. That is
destructive to the environments — fine, but say so before doing it, and prefer the single
subproject sync while iterating.

The lockfile (`uv.lock`) of the subproject changes as a result. Commit it together with the
`pyproject.toml` when asked to commit.

## Depending on another ecosim package

The subprojects consume each other through the private KIT registry, declared per
subproject:

```toml
[[tool.uv.index]]
name = "ecosim-registry"
url = "https://gitlab.kit.edu/api/v4/projects/187427/packages/pypi/simple"
authenticate = "always"
```

Authentication is a GitLab personal access token with the `read_api` scope, supplied
either through `~/.netrc`

```text
machine gitlab.kit.edu
login TOKEN_NAME
password TOKEN
```

or through `UV_INDEX_ECOSIM_REGISTRY_USERNAME` / `UV_INDEX_ECOSIM_REGISTRY_PASSWORD` — the
middle part of those names must match the index name in `pyproject.toml`.

Never write a token into a file in the repository, and never echo one into the transcript.
If a sync fails with `401`, report that the credentials are missing and let the user supply
them.

## Untyped dependencies

`mypy` runs strict. A new library without type stubs will fail the type check with
`missing imports`. Add an override to the subproject's mypy config (the root `mypy.ini`
shows the existing pattern for `fmpy`, `sqlalchemy`, `dask` and others) rather than
loosening the global settings.
