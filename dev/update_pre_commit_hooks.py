from pathlib import Path

from config import run, get_uv_path


def install_pre_commit(
    path: Path,
    dry_run: bool = False,
) -> None:
    print(f"\n==> Installing pre-commit for {path.name}")
    run([get_uv_path(), "run", "pre-commit", "install"], cwd=path, dry_run=dry_run)


def update_pre_commit(
    path: Path,
    dry_run: bool = False,
) -> None:
    print(f"\n==> Updating pre-commit for {path.name}")
    run([get_uv_path(), "run", "pre-commit", "autoupdate"], cwd=path, dry_run=dry_run)
