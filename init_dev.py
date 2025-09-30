#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

# The repository root is the directory where this script resides
REPO_ROOT = Path(__file__).resolve().parent

SUBPROJECTS: List[tuple[Path, List[str]]] = [
    (REPO_ROOT / "ecosim-common", ["dev"]),
    (REPO_ROOT / "ecosim-server", ["dev"]),
    (REPO_ROOT / "integration-tests", []),
    (REPO_ROOT / "ecosim-client-fmu-v2", ["dev"]),
    (REPO_ROOT / "ecosim-client-fmu-v3", ["dev"]),
]


def error_print(*args: object) -> None:
    print(*args, file=sys.stderr)


def run(cmd: List[str],
        cwd: Path | None = None,
        dry_run: bool = False
        ) -> None:
    as_str = " ".join(cmd)
    loc = f" (cwd={cwd})" if cwd else ""
    print(f"$ {as_str}{loc}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def pip_install_uv(dry_run: bool = False) -> None:
    # Install/upgrade uv globally using the interpreter running this script
    # -U = upgrade to the latest version
    cmd = [sys.executable, "-m", "pip", "install", "-U", "uv"]
    try:
        run(cmd, dry_run=dry_run)
    except subprocess.CalledProcessError as exc:
        error_print("Failed to install uv with pip. You can install it manually and rerun.")
        raise exc


def prepare_project(path: Path,
                    extras: Iterable[str] = (),
                    dry_run: bool = False
                    ) -> None:
    print(f"\n==> Preparing {path.name}")
    # --clear = remove existing venv dir
    run(["uv", "venv", "--clear"], cwd=path, dry_run=dry_run)
    cmd = ["uv", "sync"]
    for extra in extras:
        cmd.extend(["--extra", extra])
    run(cmd, cwd=path, dry_run=dry_run)


def install_pre_commit(path: Path,
                       dry_run: bool = False,
                       ) -> None:
    print(f"\n==> Installing pre-commit for {path.name}")
    run(["uv", "run", "pre-commit", "install"], cwd=path, dry_run=dry_run)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Initialize local dev environment with uv.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the steps without executing them.",
    )
    args = parser.parse_args(argv)

    print("Ensuring 'uv' is installed globally via pip…")
    pip_install_uv(dry_run=args.dry_run)

    for path, extras in SUBPROJECTS:
        try:
            prepare_project(path, extras, dry_run=args.dry_run)
        except subprocess.CalledProcessError as exc:
            error_print(f"Project '{path.name}' failed to prepare with error code {exc.returncode}.")
            return exc.returncode

    try:
        prepare_project(REPO_ROOT, ["dev"], dry_run=args.dry_run)
        install_pre_commit(REPO_ROOT, dry_run=args.dry_run)
    except subprocess.CalledProcessError as exc:
        error_print(f"Failed to prepare root with error code {exc.returncode}.")
        return exc.returncode

    print("\nAll requested projects are initialized.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
