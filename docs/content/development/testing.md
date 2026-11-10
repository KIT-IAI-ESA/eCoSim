# Testing

## Run the tests

- each subproject has its own virtual environment, so there is no test run in the project root
    - `cd ecosim-server && uv run pytest`
    - PyCharm can set `UV_PROJECT_ENVIRONMENT`, and `uv` then uses that environment instead of the
      subproject's `.venv`; unset it for runs by hand: `env -u UV_PROJECT_ENVIRONMENT uv run pytest`
- a single test, without the coverage report the `addopts` add:
    - `cd ecosim-server && uv run pytest tests/simulation/test_interface_value_history_thread.py -k history --no-cov`
- all subprojects except the integration tests: `python dev/run_tests.py`
    - it keeps going after a failure, prints a summary and exits non-zero if anything failed
    - subprojects without tests are reported as `no tests`, not as failures
    - limit the run: `python dev/run_tests.py ecosim-server ecosim-common`
    - forward arguments to pytest after `--`: `python dev/run_tests.py ecosim-server -- -k history --no-cov`
- a test fails after 120 s (`timeout` in the subproject's `pyproject.toml`), switch that off in a debugger or for a long local run: `--timeout=0`

| Subproject | Tests |
| --- | --- |
| `ecosim-common`, `ecosim-server`, `ecosim-client-fmu-v2`, `ecosim-client-fmu-v3`, `ecosim-client-matlab`, `ecosim-hpc` | `tests/` |
| `integration-tests` | `integration_tests/` |
| `ecosim-common-fmpy`, `ecosim-client-pyro5`, `ecosim-test-common` | none |

`ecosim-server/tests/tech/db/` starts its own throwaway PostgreSQL clusters on a free port if `initdb`
is installed. Without `initdb`, and in CI, those tests are skipped.

Mark a test that loads an FMU with `@skip_unless_fmpy_loads(fmu_file)` from `ecosim_test_common/fmpy_platform.py`,
so it is skipped where fmpy cannot load the FMU's binary. For the house FMUs, use
`@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()`, which also skips the platforms that have no build of them.

The applications parse `sys.argv` themselves and reject unknown arguments. A test that starts one
calls `esp_monkey_patch.remove_pytest_sys_args()` from `ecosim-test-common` before it sets its own
arguments. Otherwise it passes under `pytest` but fails under `pytest -q` or in an IDE.

## Integration tests

- `cd integration-tests && uv run pytest --ignore=integration_tests/locally`
- they import the other subprojects, so sync after changing one: `python dev/sync_projects.py`
- some start PostgreSQL through `testcontainers`, so they need Docker
- the tests in `integration_tests/locally/` need external models or an HPC environment, so the
  command above skips them, as CI does
- `integration_tests/server_client/` runs a real server against real clients for every protocol and
  storage backend, the quickest way to see a whole run

### Simulations

`ecosim_test_common/resources/simulations/` holds complete simulations with their expected results:

- `HouseSimulationData`: weather, house, heating and ventilation as FMI 2.0 FMUs, 200 steps. The
  resources are in `resources/fmu_v2/models/house/`, with one FMU build per platform (`linux/`,
  `windows/`). `integration-tests/integration_tests/server_client/house_simulation/` runs it and
  is the example to follow for a test of a whole simulation.

## Performance tests

The performance tests in `integration-tests/integration_tests/server_client/performance/` are not sophisticated
performance tests. They run the integration tests of `server_client/` and a long running house simulation, and compare
the times of each run with the expected times of the same test, machine and protocol. So they only show bigger
deviations; the tolerances are in `tooling/performance_setup.py`. A summary of all times is printed at the end of the
run.

- run them: `python dev/run_performance_tests.py` (arguments are forwarded to pytest, e.g. `-k batch_steps`)
- create new expected data (locally): `python dev/create_performance_test_data.py` runs them several times (`--repetitions N`)
  and writes the mean of each time as new expected data
- create new expected data (GitHub): `.github/workflows/performance-tests.yml` runs them and `.github/workflows/create-performance-test-data.yml`
  (manual trigger) creates new expected data; both upload their results as artifacts, commit them to make them
  the expected data of later runs

The results are stored as JSON lines in `integration-tests/integration_tests/resources/performance/`, one file per
date, protocol and machine (`DATE_TIME_PROTOCOL_MACHINE.jsonl`). The files in the folder itself are the expected data,
every run writes its results and its summary to `actual/` (git-ignored). Historical data is available in `historical/`.

Environment variables:

- `ECOSIM_PERFORMANCE_MACHINE`: overwrite the machine name that's running the tests; `local_*` are local machines, `github_ci_*` runs on
  GitHub (the workflows use `github_ci_default`); default `local_<host name>`
  - the machine name is also used to match with the expected data
  - the specs of the machines are in [Performance Machines](performance/performance-machines.md)
- `ECOSIM_MACHINE_NAME_FOR_FALLBACK_LOCAL_REPOSITORY`: a local machine without expected data of its own is compared
  with the expected data of this machine; default `local_tuxedo_infinity_book_pro_15_gen9_amd`


## Before a commit

1. pre-commit on the changed files: `uv run pre-commit run --files $(git diff --name-only --diff-filter=d HEAD)`
    - `git diff` does not list new files, so `git add` them first or pass them as well
    - some hooks rewrite files (whitespace, trailing commas, ruff), so run it again until it reports nothing
    - after a change across many subprojects, `--all-files` is the thorough check; it runs mypy for every
      subproject and takes minutes
2. mypy for each changed subproject: `python dev/run_mypy.py ecosim-server`
    - each subproject has its own `[tool.mypy]`; the root `mypy.ini` is only for the IDE
    - the hook `mypy (dev)` checks the scripts in `dev/` with `--strict`; to check one by hand:
      `MYPYPATH=dev uv run mypy --strict --ignore-missing-imports dev/<script>.py`
3. the tests of each changed subproject; after a change to `ecosim-common`, all of them
4. a quick end-to-end run: `cd integration-tests && uv run pytest integration_tests/server_client/test_three_client_server.py`

The workflow `.github/workflows/tests.yml` runs these checks on GitHub for every pull request and every push to `main`.
A pull request can only be merged when `tests-passed`, `docs-reference`, `docs-build` and `commit-messages` pass.

## Secret leaks

[Betterleaks](https://github.com/betterleaks/betterleaks) looks for leaked secrets such as passwords, tokens and API keys.

- the pre-commit hook `betterleaks` checks the staged changes on every commit
- `python dev/check_for_leaked_secrets.py` checks the whole git history; the job `leaked-secrets` in
  `.github/workflows/tests.yml` runs it on GitHub
- known leaks, e.g. the passwords of test databases, are listed in `.betterleaksignore` and no longer reported;
  `python dev/check_for_leaked_secrets.py --interactive-update-known-leaks` shows every new leak and asks whether to
  add it there
- GitHub CI does the full history scan
