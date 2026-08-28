# Developing

## Add new dependencies

- add the dependency in the corresponding `pyproject.toml` of the subproject
- **either** run `uv sync` / `uv sync --extra dev` inside the folder of the subproject
- **or** run the script `dev/sync_projects.py`
  - `python dev/sync_projects`
- **or** with PyCharm you can run the run config `sync projects`

## Run the tests

- each subproject has its own virtual environment, so there is no test run in the project root
    - `cd ecosim-server && uv run pytest`
- to run all tests except the integration tests, use the script `dev/run_tests.py`
    - `python dev/run_tests.py`
    - it keeps going after a failure, prints a summary and exits non-zero if anything failed
    - limit the run to single subprojects: `python dev/run_tests.py ecosim-server`
    - forward arguments to pytest after `--`: `python dev/run_tests.py ecosim-server -- -k history`
        - by default no pytest arguments are passed, because the tests of `ecosim-hpc` read
          `sys.argv` and fail on entries they do not know
- the integration tests are run separately, they need real ports and containers
    - `cd integration-tests && uv run pytest`
