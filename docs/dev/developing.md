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
        - by default no pytest arguments are passed
- the integration tests are run separately, they need real ports and containers
    - `cd integration-tests && uv run pytest`

## Build the documentation

- the site is rendered from `docs/` with [mkdocs](https://www.mkdocs.org/) and the
  [material](https://squidfunk.github.io/mkdocs-material/) theme, configured in `mkdocs.yml`
- install the dependencies once (in the project root)
    - `uv sync --extra dev --extra doc`
- serve it locally with live reload
    - `uv run mkdocs serve`
- build it the way CI does - `--strict` fails on a broken link or a page missing from the `nav`
    - `uv run mkdocs build --strict`
    - the output goes to `site/`, which is gitignored
- it is published from both forges
    - GitLab: the `pages` job in `.gitlab-ci.yml`, on the default branch only
    - GitHub: `.github/workflows/doc.yml`
    - every other branch and pull request only builds, it does not publish
- a new page has to be added to the `nav` in `mkdocs.yml`, otherwise `--strict` will not accept it
