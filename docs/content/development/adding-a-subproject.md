# Adding a subproject

A new subproject is not picked up automatically. Three places change together; if one is missing,
the package is never synced or type checked, and nothing reports it.

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

`dev/sync_projects.py`, `dev/init_dev.py` and `dev/run_tests.py` go through this list.

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

## Finally

```shell
python dev/sync_projects.py
uv run pre-commit run --all-files
```

Add the subproject to the table in [Architecture](architecture.md) as well.
