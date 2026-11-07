import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable
from config import run, SUBPROJECTS, error_print, REPO_ROOT, get_uv_path


def sync_project(
    path: Path,
    extras: Iterable[str] = (),
    dry_run: bool = False,
    clear_venv: bool = True,
    locked: bool = False,
) -> None:
    print(f"\n==> Preparing {path.name}")
    # --clear = remove existing venv dir
    uv_path = get_uv_path()
    if clear_venv:
        run([uv_path, "venv", "--clear"], cwd=path, dry_run=dry_run)
    cmd = [uv_path, "sync"]
    if locked:
        cmd.append("--locked")
    for extra in extras:
        cmd.extend(["--extra", extra])
    run(cmd, cwd=path, dry_run=dry_run)


def sync_all_projects(dry_run: bool = False, locked: bool = False) -> bool:
    print("Syncing all projects...")
    succeeded = True
    for path, extras in SUBPROJECTS:
        try:
            sync_project(path=path, extras=extras, dry_run=dry_run, locked=locked)
        except subprocess.CalledProcessError as exc:
            succeeded = False
            error_print(f"Project '{path.name}' failed to prepare with error code {exc.returncode}.")
    try:
        sync_project(path=REPO_ROOT, extras=["dev"], dry_run=dry_run, clear_venv=False, locked=locked)
    except subprocess.CalledProcessError as exc:
        succeeded = False
        error_print(f"Failed to prepare root with error code {exc.returncode}.")

    print("Syncing all projects...done.")
    return succeeded


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Recreate the virtual environment of every subproject and sync it, then sync the root.")
    parser.add_argument("--locked", action="store_true", help="Fail if a uv.lock is out of date instead of updating it, as CI does.")
    options = parser.parse_args(arguments)
    return 0 if sync_all_projects(locked=options.locked) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
