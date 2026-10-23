# Developing

## Add new dependencies

- add the dependency in the corresponding `pyproject.toml` of the subproject
- **either** run `uv sync` / `uv sync --extra dev` inside the folder of the subproject
- **or** run the script `dev/sync_projects.py`
  - `python dev/sync_projects.py`
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

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/), checked by `dev/check_commit_msg.py`:

```text
<type>[(<scope>)][!]: <summary>

[optional body, e.g. Closes #12]
```

- types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- summary in the imperative: `add`, not `added`
- `!` marks a breaking change
- the check runs as a `commit-msg` hook after `uv run pre-commit install`, and on GitHub for every new commit

## Documentation

The documentation is a [Docusaurus](https://docusaurus.io/) site in `docs/`. The pages are
Markdown files in `docs/content/`, the sidebar is defined in `docs/sidebars.ts`. It needs
Node.js 20 or newer.

- install the dependencies once: `cd docs && npm ci`
- serve it locally with live reload: `npm start`
- build it the way CI does: `npm run build`
    - the build fails on a broken link, so run it before handing the work back
    - the output goes to `docs/build/`, which is gitignored
- a new page has to be added to `docs/sidebars.ts`

### Generated reference

The two reference pages are generated from the code. After changing a command-line option or a
config reader, regenerate them in the repository root:

- `uv run --project simulation_examples python dev/generate_cli_reference.py`
- `uv run python dev/generate_config_reference.py`

With `--check`, both scripts only compare and fail if the page is out of date. CI runs them this way.

### Publishing

The workflow `.github/workflows/docs.yml` builds the site for every push and pull request, and
publishes `main` to GitHub Pages.
