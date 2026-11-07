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

## 2. `dev/config.py`

Add it to `SUBPROJECTS`, with the extras to sync:

```python
(REPO_ROOT / "ecosim-<name>", ["dev"]),
```

`dev/sync_projects.py`, `dev/init_dev.py`, `dev/run_tests.py` and `dev/bump_version.py` go through this list.

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

The `unit-tests` job runs `dev/run_tests.py` for each subproject in its matrix. Add the new one,
unless it is one of the `EXCLUDED_PROJECTS` in `dev/run_tests.py`:

```yaml
      matrix:
        project:
          - ecosim-<name>
```

## Finally

```shell
python dev/sync_projects.py
uv run pre-commit run --all-files
```

Add the subproject to the table in [Architecture](architecture.md) as well.
