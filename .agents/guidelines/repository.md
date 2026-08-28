# Repository Guidelines

Facts about this repository that are easy to get wrong. Read this before running any command.

## It is a monorepo of independent uv projects

Every subproject has **its own** `pyproject.toml`, `uv.lock` and `.venv`. There is no
root virtual environment that can import the subprojects, and there is no root test run.

Always work from inside the subproject:

```shell
cd ecosim-server && uv run pytest
```

The root `.venv` exists only for the development tooling (`pre-commit`, `mypy`, `ruff`).

| Subproject | Import package | Purpose |
|---|---|---|
| `ecosim-common` | `ecosim_common` | Shared abstractions: config, communication, simulation primitives |
| `ecosim-common-fmpy` | `ecosim_common_fmpy` | Shared FMU/fmpy code for the FMU clients |
| `ecosim-server` | `ecosim_server` | The simulation server: state, repositories, measurements |
| `ecosim-client-fmu-v2` | `ecosim_client_fmu_v2` | Client for FMI 2.0 models |
| `ecosim-client-fmu-v3` | `ecosim_client_fmu_v3` | Client for FMI 3.0 models |
| `ecosim-client-matlab` | `ecosim_client_matlab` | Client for Matlab models |
| `ecosim-client-pyro5` | `ecosim_client_pyro5` | Client bridging via Pyro5 |
| `ecosim-hpc` | `ecosim_hpc` | HPC entry point and client manager |
| `ecosim-test-common` | `ecosim_test_common` | Shared fixtures, test data and FMU resources |
| `integration-tests` | `integration_tests` | Cross-package tests, needs the others installed |

`dev/config.py:SUBPROJECTS` is the authoritative list — the tooling iterates over it.

## Syncing

After changing any dependency, run from the repository root:

```shell
python dev/sync_projects.py
```

This recreates every subproject `.venv` (`uv venv --clear`) and syncs it. It is destructive
to the environments but never to source. `python dev/init_dev.py` is the first-time setup.

## The server has two storage backends

`DatabaseType` is `postgres` or `file`. The `file` backend appends JSON lines to a
directory and needs no database. Both are configured through the `[database]` section of
the server ini, and both are exercised by `dev/docker/example/`.

## Conventions the tooling enforces

- Python filenames must be `snake_case` (`dev/validate_file_name.py`).
- Line length is 150 everywhere (`ruff`, `flake8`, `.editorconfig`).
- Trailing commas are added automatically for multi-line calls (`add-trailing-comma`).
- `mypy` runs with `disallow_untyped_defs` — every signature needs annotations.
- `f-strings in log calls are rejected` (ruff `G004`); pass lazy `%s` arguments instead.

## Never

- Never commit or push unless explicitly asked.
- Never run `python dev/sync_projects.py` just to "fix" an import error without saying so —
  it wipes the virtual environments.
