# Adding a subproject

A new subproject is not picked up automatically. Four places change together; if one is missing,
the package is never synced, tested or type checked. `uv run pytest dev/tests` reports a subproject
that is in `dev/config.py` but missing from the mypy hooks or the test matrix.

## 1. The package

```text
ecosim-<name>/
  pyproject.toml
  uv.lock               generated
  ecosim_<name>/
    __init__.py
    py.typed            if other packages import it
  tests/
```

- the folder uses hyphens, the import package underscores
- copy the `pyproject.toml` of the closest sibling; every subproject has its own
  `[tool.pytest.ini_options]` and `[tool.mypy]`
- a published package needs its own copy of the root `LICENSE` and `NOTICE`; `license-files` cannot
  point outside the package folder
- it also needs a copy of `PYPI_NOTE.md` from a sibling: the note "part of the eCoSim project" that PyPI
  shows above the README, through `[tool.setuptools.dynamic] readme`; the README itself stays as GitHub
  shows it

## 2. `dev/config.py`

Add it to `SUBPROJECTS`, with the extras to sync:

```python
(REPO_ROOT / "ecosim-<name>", ["dev"]),
```

`dev/sync_projects.py`, `dev/init_dev.py`, `dev/run_unit_tests.py` and `dev/release/bump_version.py` go through this list.

## 3. `.pre-commit-config.yaml`

mypy runs once per subproject. Add a hook next to the others:

```yaml
      - id: mypy
        name: mypy (ecosim-<name>)
        entry: python dev/run_mypy.py ecosim-<name>
        language: system
        files: ^ecosim-<name>/
        pass_filenames: false
        types: [ python ]
```

## 4. `.github/workflows/tests.yml`

The `unit-tests` job runs `dev/run_unit_tests.py` for each subproject in its matrix. Add the new one,
unless it is one of the `EXCLUDED_PROJECTS` in `dev/run_unit_tests.py`:

```yaml
      matrix:
        project:
          - ecosim-<name>
```

## 5. `.github/workflows/release.yml`, if it is published

Only the packages in `PACKAGES` are published to PyPI. Add a package that users install:

```yaml
env:
  PACKAGES: >-
    ecosim-<name>
```

Before its first release, add a pending trusted publisher for it on PyPI, with the values of the
[one-time setup](releasing.md#one-time-setup). PyPI accepts only one pending publisher per repository,
workflow and environment, so a release can create only one new package; for more, upload them once
by hand as in [First release](releasing.md#first-release).

## Finally

```shell
python dev/sync_projects.py
uv run pre-commit run --all-files
```

Add the subproject to the table in [Architecture](architecture.md) as well.
