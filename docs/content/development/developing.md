# Developing

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/), checked by `dev/check_commit_message.py`:

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
Node.js 20 or newer, or Docker with the script below.

- install the dependencies once: `cd docs && npm ci`
- serve it locally with live reload: `npm start`
- build it the way CI does: `npm run build`
    - the build fails on a broken link, so run it before handing the work back
    - the output goes to `docs/build/`, which is gitignored
- or install and build in one step from the repository root: `python dev/build_docs.py`
    - it uses npm, or a pinned `node:20` image in Docker if npm is not installed
    - `--npm` or `--docker` picks one; the files in `docs/` stay yours with either
    - `--serve` serves it with live reload on `http://localhost:3000/ecosim-os/` instead of building
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
