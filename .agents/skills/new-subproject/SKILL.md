---
name: new-subproject
description: Add a new subproject (package) to the monorepo. Use when a new ecosim-* package is created - four places must be changed in lockstep or the tooling silently skips it.
---

# Add a new subproject

A new package is not picked up automatically. Four places must change together; missing one
fails quietly — the package simply is never checked or tested.

## 1. The package itself

```
ecosim-<name>/
  pyproject.toml
  uv.lock              (generated)
  ecosim_<name>/
    __init__.py
    py.typed           if the package is imported by others
  tests/
```

Directory name uses hyphens, the import package uses underscores. Copy the
`pyproject.toml` of the closest existing sibling — the `[tool.pytest.ini_options]` and
`[tool.mypy]` blocks are per subproject and are expected to be present.

## 2. `dev/config.py`

Append to `SUBPROJECTS`, with the extras it needs synced:

```python
(REPO_ROOT / "ecosim-<name>", ["dev"]),
```

This is what `dev/sync_projects.py` and `dev/init_dev.py` iterate over. Not listed means
never synced.

## 3. `.pre-commit-config.yaml`

`mypy` is registered once **per subproject** in the `local` repo section. Add a hook
mirroring the existing ones:

```yaml
      - id: mypy
        name: mypy (ecosim-<name>)
        entry: python dev/run_mypy.py ecosim-<name>
        language: system
        files: ^ecosim-<name>/
        pass_filenames: false
        types: [ python ]
```

Not listed means the package is never type checked.

## 4. `.gitlab-ci.yml`

Add the path to the `PROJECT_DIR` matrix of `.sub-project-template`:

```yaml
          - $SRC_DIR/ecosim-<name>
```

That matrix drives both the `my_py` and the `test` job. Note that the matrix is currently
narrower than `SUBPROJECTS` — decide deliberately whether the new package belongs in CI,
and say which you chose.

## Finally

```shell
python dev/sync_projects.py
uv run pre-commit run --all-files
```

Then update `doc/dev/` if the new package changes how the project is set up.
