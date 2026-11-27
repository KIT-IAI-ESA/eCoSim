# Releasing

All eCoSim packages are released together, with one version, from `main`. A pull request sets the
new version, a manual start of a workflow releases it; nothing is bumped or uploaded by hand. Only the
very first release is uploaded by hand, see [First release](#first-release).

## Development happens in the monorepo

The packages on PyPI are for using eCoSim. Developing it, its tests and its fixes happen in this
repository only, see [Project setup](project-setup.md):

- the subprojects use each other from the working tree (`[tool.uv.sources]`), and a change often
  touches several of them at once
- the `dev` extras need `ecosim-test-common`, **which is not published**, so an extra like
  `ecosim-server[dev]` cannot be installed from PyPI
- there is no repository per package; issues and pull requests go to this one

## Versions

- every package has the same version, and the packages pin each other exactly: `ecosim-common==1.0.0`
- a release publishes every package with the new version, even one that did not change, so the pins
  between them always match
- the version on `main` is the version of the last release, or of the one being released; it is
  only changed by the pull request of a release, never by hand

## Make a release

1. on GitHub, open Actions → `prepare release` → Run workflow, keep the branch `main` and enter the
   version without the `v`, e.g. `1.0.0`
2. it opens the pull request `chore(release): 1.0.0` from the branch `release/v1.0.0`; add the notes
   of the version to the [release history](release-history.md) on that branch
3. merge the pull request once the checks pass
4. open Actions → `release` → Run workflow, keep the branch `main` and enter the version again;
   the run stops if `main` does not have it, e.g. because the pull request is not merged yet
5. if the `pypi` environment asks for a review, approve the deployment

The scripts of a release are in `dev/release/`. They import `dev/config.py`, so they run as modules
from `dev/`: `cd dev && python -m release.bump_version 1.0.0`.

`.github/workflows/prepare-release.yml` checks the version with `python -m release.check_new_version`:
it has to look like `1.0.0`, be newer than the latest release tag and than the version on `main` (which
may be merged but not released yet), and neither the tag nor the release
branch may exist. It sets the version of every package and every pin with `python -m release.bump_version`,
pushes the release branch and opens the pull request. A pull request opened by a workflow starts no
other workflow, so it starts `tests.yml` on the branch itself.

`.github/workflows/release.yml` is started by hand on `main`:

| Job | What it does |
| --- | --- |
| `build` | `python -m release.check_release` stops the release unless every package on `main` has the entered version, it is newer than the latest release tag, its tag does not exist yet and no package has it on PyPI yet; `python -m release.build_release_packages` builds the sdist of each package in `PACKAGES` and the wheel from it, without `[tool.uv.sources]` (`--no-sources`); the wheels are installed into a new environment outside the repository, every package is imported and every command runs with `--help` |
| `publish` | uploads the packages to PyPI with trusted publishing (no token), then creates the tag `v1.0.0` on the released commit and the GitHub release with the packages and generated notes |

The tag is created last, so until the packages are on PyPI, the version counts as not released.

## When a run fails

- `prepare release` fails before it pushes anything: fix the cause and start it again; if it failed
  after pushing the branch, delete the branch `release/v1.0.0` (and its pull request) first
- a failed release is repeated with "Re-run failed jobs" of the same run, which publishes the packages
  of the same commit; the upload skips the files that are on PyPI already
- a new start of `release` refuses a version that is partly on PyPI already; otherwise, after `main` moved on, it
  would mix the files of two commits under one version

## Published packages

`PACKAGES` in `release.yml` lists the packages that are published, each as a PyPI project of its own:
`ecosim-common`, `ecosim-common-fmpy`, `ecosim-server`, `ecosim-client-fmu-v2`, `ecosim-client-fmu-v3`,
`ecosim-client-matlab`, `ecosim-client-pyro5`, `ecosim-client-python`, `ecosim-cli` and `ecosim-hpc`.

`ecosim-test-common`, `integration-tests` and `examples` are not published. A new package is only
published once it is in `PACKAGES` and has a trusted publisher on PyPI, see
[Adding a subproject](adding-a-subproject.md).

On PyPI, each package page shows the note "part of the eCoSim project" from its `PYPI_NOTE.md` above
its `README.md`; `[tool.setuptools.dynamic] readme` in its `pyproject.toml` joins the two files. On
GitHub, the README stays as it is.

## One-time setup

*This is mainly kept as a historical reference, since this is a one-time setup.*

- on GitHub, the environment `pypi`, with only `main` under "Deployment branches and tags", optionally
  with required reviewers
- in the repository settings, Actions → General → "Allow GitHub Actions to create and approve pull
  requests", for `prepare release`
- on PyPI, every published package has a trusted publisher: owner `KIT-IAI-ESA`, repository `eCoSim`,
  workflow `release.yml`, environment `pypi`; any number of existing projects may share it

### First release

A workflow can only create a new PyPI project through a *pending* trusted publisher, and PyPI accepts
only one pending publisher per repository, workflow and environment. So `release` cannot create the
projects of the first release; they are uploaded once by hand:

1. prepare the version with `prepare release` and merge its pull request, but do not start `release`
2. build every package on `main`:
   `cd dev && python -m release.build_release_packages <every package of PACKAGES> && cd ..`
3. on pypi.org, create an API token with the scope "Entire account" (a project scope needs an existing
   project) and upload: `UV_PUBLISH_TOKEN=<token> uv publish --check-url https://pypi.org/simple/ dist/*`
4. add the trusted publisher of the [one-time setup](#one-time-setup) to every new project, then delete
   the token
5. create the tag and the GitHub release that `release` would create:
   `gh release create v<version> dist/* --target "$(git rev-parse HEAD)" --generate-notes`
6. check that the packages install from PyPI:
   `uv run --no-project --python 3.12 --with ecosim-cli==<version> -- ecosim --help`

From the next version on, `release` does all of this. An API token in the workflow instead would be
long-lived, valid for every project of the account, and allows no attestations.
