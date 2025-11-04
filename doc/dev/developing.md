# Developing

## Add new dependencies

- add the dependency in the corresponding `pyproject.toml` of the subproject
- **either** run `uv sync` / `uv sync --extra dev` inside the folder of the subproject
- **or** run the script `dev/sync_projects.py`
  - `python dev/sync_projects`
- **or** with PyCharm you can run the run config `sync projects`
