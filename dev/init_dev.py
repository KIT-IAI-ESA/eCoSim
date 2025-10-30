#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List

from config import run, error_print, REPO_ROOT
from sync_projects import sync_all_projects
from update_pre_commit_hooks import install_pre_commit, update_pre_commit


def pip_install_uv(dry_run: bool = False) -> None:
    # Install/upgrade uv globally using the interpreter running this script
    # -U = upgrade to the latest version
    cmd = [sys.executable, "-m", "pip", "install", "-U", "uv"]
    try:
        run(cmd, cwd=REPO_ROOT, dry_run=dry_run)
    except subprocess.CalledProcessError as exc:
        error_print("Failed to install uv with pip. You can install it manually and rerun.")
        raise exc


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

    sync_all_projects(dry_run=args.dry_run)
    install_pre_commit(REPO_ROOT, dry_run=args.dry_run)
    update_pre_commit(REPO_ROOT, dry_run=args.dry_run)

    print("\nAll requested projects are initialized.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
