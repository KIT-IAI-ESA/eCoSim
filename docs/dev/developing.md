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

## Build the documentation

- the site is rendered from `docs/` with [mkdocs](https://www.mkdocs.org/) and the
  [material](https://squidfunk.github.io/mkdocs-material/) theme, configured in `mkdocs.yml`
- use the script `dev/run_mkdocs.py` to run mkdocs locally
- or do it by hand, in the project root
  - install the dependencies once: `uv sync --extra dev --extra doc`
  - serve it locally with live reload: `uv run mkdocs serve`
  - build it the way CI does: `uv run mkdocs build --strict`
    - `--strict` fails on a broken link or a page missing from the `nav`, so a new page has to be
        added to the `nav` in `mkdocs.yml`
  - the output goes to `site/`, which is gitignored
  - `serve` runs without `--strict`, otherwise a half-written link would kill the running server.
    Run `build` before handing the work back
  - the script serves the site at the root URL (it sets `SITE_URL` to empty). `mkdocs serve` on its
    own puts it under the forge path from `site_url`, e.g. `http://127.0.0.1:8000/kit/iai/esa/ecosim/`

### Publishing

!!! warning "GitLab Pages is disabled on the KIT GitLab"

    The `pages` job in `.gitlab-ci.yml` builds the site and keeps it as an artifact, but the KIT
    instance (`gitlab.kit.edu`) has GitLab Pages switched off instance-wide, so nothing is served
    from it. There is no per-project setting that turns it on. Until that changes, read the docs
    locally with `dev/run_mkdocs.py`, or download the `public` artifact of the `pages` job.

- the `doc_build` job builds every non-default branch as a link check, it never publishes
- the `pages` job runs on the default branch only
