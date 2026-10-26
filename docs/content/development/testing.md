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

| Subproject | Tests |
| --- | --- |
| `ecosim-common`, `ecosim-common-fmpy`, `ecosim-server`, `ecosim-client-fmu-v2`, `ecosim-client-fmu-v3`, `ecosim-client-matlab`, `ecosim-hpc` | `tests/` |
| `integration-tests` | `integration_tests/` |
| `ecosim-client-pyro5`, `ecosim-test-common` | none |

The applications parse `sys.argv` themselves and reject unknown arguments. A test that starts one
calls `esp_monkey_patch.remove_pytest_sys_args()` from `ecosim-test-common` before it sets its own
arguments. Otherwise it passes under `pytest` but fails under `pytest -q` or in an IDE.

## Integration tests

- `cd integration-tests && uv run pytest --ignore=integration_tests/locally`
- they import the other subprojects, so sync after changing one: `python dev/sync_projects.py`
- some start a real server on port `1234` and PostgreSQL through `testcontainers`, so they cannot
  run while a Docker example uses that port
- the tests in `integration_tests/locally/` need external models or an HPC environment, so the
  command above skips them, as CI does
- `integration_tests/server_client/` runs a real server against real clients for every protocol and
  storage backend, the quickest way to see a whole run

## Before a commit

1. pre-commit on the changed files: `uv run pre-commit run --files $(git diff --name-only --diff-filter=d HEAD)`
    - `git diff` does not list new files, so `git add` them first or pass them as well
    - some hooks rewrite files (whitespace, trailing commas, ruff), so run it again until it reports nothing
    - after a change across many subprojects, `--all-files` is the thorough check; it runs mypy for every
      subproject and takes minutes
2. mypy for each changed subproject: `python dev/run_mypy.py ecosim-server`
    - each subproject has its own `[tool.mypy]`; the root `mypy.ini` is only for the IDE
    - the mypy hooks do not cover `dev/`, check a changed script with
      `MYPYPATH=dev uv run mypy --strict --ignore-missing-imports dev/<script>.py`
3. the tests of each changed subproject; after a change to `ecosim-common`, all of them
4. a quick end-to-end run: `cd integration-tests && uv run pytest integration_tests/server_client/test_three_client_server.py`

The workflow `.github/workflows/tests.yml` runs these checks on GitHub for every pull request and every push to `main`.
