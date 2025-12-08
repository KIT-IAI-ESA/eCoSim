import subprocess
from pathlib import Path
from typing import Iterable
from config import run, SUBPROJECTS, error_print, REPO_ROOT, get_uv_path


def sync_project(
    path: Path,
    extras: Iterable[str] = (),
    dry_run: bool = False,
    clear_venv: bool = True,
) -> None:
    print(f"\n==> Preparing {path.name}")
    # --clear = remove existing venv dir
    uv_path = get_uv_path()
    if clear_venv:
        run([uv_path, "venv", "--clear"], cwd=path, dry_run=dry_run)
    cmd = [uv_path, "sync"]
    for extra in extras:
        cmd.extend(["--extra", extra])
    run(cmd, cwd=path, dry_run=dry_run)


def sync_all_projects(dry_run: bool = False) -> None:
    print("Syncing all projects...")
    for path, extras in SUBPROJECTS:
        try:
            sync_project(path, extras, dry_run=dry_run)
        except subprocess.CalledProcessError as exc:
            error_print(f"Project '{path.name}' failed to prepare with error code {exc.returncode}.")
    try:
        sync_project(REPO_ROOT, ["dev"], dry_run=dry_run, clear_venv=False)
    except subprocess.CalledProcessError as exc:
        error_print(f"Failed to prepare root with error code {exc.returncode}.")

    print("Syncing all projects...done.")


if __name__ == "__main__":
    sync_all_projects()
