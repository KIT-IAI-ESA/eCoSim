---
name: run-tests
description: Run the unit or integration tests of this monorepo. Use whenever tests need to be executed or verified after a change - the tests cannot be started from the repository root, each subproject has its own virtual environment.
---

# Run tests

## There is no root test run

Each subproject carries its own `.venv`. Running `pytest` from the repository root finds
nothing useful and fails on imports. Always change into the subproject first:

```shell
cd ecosim-server && uv run pytest
```

`uv run` picks up that subproject's environment. Do not activate a venv manually.

## A single test

The `addopts` in each `pyproject.toml` already add coverage, `--junitxml` and `-v`, which
is noisy for a single test. Turn coverage off when iterating:

```shell
cd ecosim-server && uv run pytest tests/simulation/test_interface_value_history_thread.py -k history --no-cov
```

## Which subprojects have tests

| Subproject | Test location |
|---|---|
| `ecosim-common`, `ecosim-common-fmpy`, `ecosim-server`, `ecosim-client-fmu-v2`, `ecosim-client-fmu-v3`, `ecosim-client-matlab`, `ecosim-hpc` | `tests/` |
| `integration-tests` | `integration_tests/` |
| `ecosim-client-pyro5`, `ecosim-test-common` | no `testpaths` configured, and no tests |

## Every subproject at once

Use the script, from the repository root:

```shell
python dev/run_tests.py
```

It runs `uv run pytest` in every subproject except `integration-tests` and
`ecosim-test-common`, keeps going after a
failure, prints a summary, and exits non-zero if anything failed. Subprojects without tests
are reported as `no tests` rather than as failures (pytest exits with 5 when it collects
nothing).

Limit the run, or forward arguments to pytest after `--`:

```shell
python dev/run_tests.py ecosim-server ecosim-common
python dev/run_tests.py ecosim-server -- -k history --no-cov
```

The script passes no pytest arguments by default.

A test must not depend on how the runner was invoked. The applications parse `sys.argv`
themselves and reject arguments they do not know, so a test that drives one has to call
`ESPMonkeyPatch.remove_pytest_sys_args()` before setting its own arguments — otherwise the
runner's arguments are still there, and the test passes under `pytest` but fails under
`pytest -q` or under the test path an IDE passes.

CI (`.gitlab-ci.yml`) only runs the matrix `ecosim-common`, `ecosim-client-fmu-v2`,
`ecosim-client-fmu-v3`, `ecosim-client-matlab`, `ecosim-server`. A green pipeline therefore
does **not** prove `ecosim-hpc`, `ecosim-client-pyro5` or `integration-tests` still pass —
`dev/run_tests.py` covers the first two, the integration tests stay manual.

## Integration tests

`integration-tests` imports the other packages, so it must be synced after changes to them
(`python dev/sync_projects.py`). Its `addopts` contain `--ignore=locally`: the tests under
`integration_tests/locally/` are manual, need external models or an HPC environment, and are
excluded from the normal run. Do not "fix" them by removing that ignore.

Some integration tests start a real server on a real port and use `testcontainers` for
postgres. They are slow and cannot run in parallel with the docker examples, which occupy
port 1234.

## Reporting

State the actual outcome. If tests fail, quote the failing assertion. Never report a test
run as green without having seen the summary line.
