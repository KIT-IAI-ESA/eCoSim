#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from typing import List

from config import error_print, REPO_ROOT
from sync_projects import sync_all_projects
from update_pre_commit_hooks import install_pre_commit

UV_INSTALLER_URL = "https://docs.astral.sh/uv/getting-started/installation/"


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Initialize local dev environment with uv.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the steps without executing them.",
    )
    args = parser.parse_args(argv)

    if shutil.which("uv") is None:
        error_print(f"'uv' is not on PATH. Install it with the official installer: {UV_INSTALLER_URL}")
        return 1

    sync_all_projects(dry_run=args.dry_run)
    install_pre_commit(REPO_ROOT, dry_run=args.dry_run)

    print("\nAll requested projects are initialized.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
