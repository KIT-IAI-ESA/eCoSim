#!/usr/bin/env python3
"""Serves or builds the documentation site with mkdocs, from anywhere in the repository."""

import os
import subprocess
import sys
from typing import Dict, List, Sequence, Tuple

from config import REPO_ROOT, error_print, get_uv_path

# The mkdocs dependencies live in the root project, in the 'doc' extra. 'dev' is synced along
# with it: the root venv holds exactly the extras of the last sync, and dropping 'dev' would take
# pre-commit and mypy out of it.
ROOT_EXTRAS = ("dev", "doc")

# 'build' is the check CI runs, so it gets the same '--strict'. 'serve' stays lenient: with
# '--strict' a broken link while writing kills the running server instead of showing the page
COMMANDS: Dict[str, List[str]] = {"serve": [], "build": ["--strict"]}

USAGE = """Usage: python dev/run_mkdocs.py [serve|build] [--no-sync] [mkdocs argument ...]

Runs mkdocs in the repository root, where mkdocs.yml lives.

  python dev/run_mkdocs.py                     install and serve with live reload, mkdocs prints the URL
  python dev/run_mkdocs.py build               build into site/ with --strict, the way CI does
  python dev/run_mkdocs.py serve -a :8080      forward arguments to mkdocs
  python dev/run_mkdocs.py --no-sync           skip 'uv sync', use the venv as it is

'build' fails on a broken link or a page missing from the 'nav' of mkdocs.yml."""


def mkdocs_environment(serving: bool = False) -> Dict[str, str]:
    """'uv run' warns about and ignores an active venv of another project, so it is removed."""
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    if serving:
        # without this the site_url of mkdocs.yml puts the local server under the forge path
        environment["SITE_URL"] = ""
    return environment


def run_in_root(command: List[str], serving: bool = False) -> int:
    print(f"\n==> {' '.join(command)} (cwd={REPO_ROOT})", flush=True)
    return subprocess.run(command, cwd=str(REPO_ROOT), env=mkdocs_environment(serving)).returncode


def split_arguments(argv: Sequence[str]) -> Tuple[str, bool, List[str]]:
    """Splits '[serve|build] [--no-sync] <mkdocs argument ...>' into its three parts."""
    arguments = [argument for argument in argv if argument != "--no-sync"]
    command = arguments.pop(0) if arguments and arguments[0] in COMMANDS else "serve"
    return command, "--no-sync" not in argv, arguments


def extra_arguments() -> List[str]:
    return [argument for extra in ROOT_EXTRAS for argument in ("--extra", extra)]


def superfluous_commands(argv: Sequence[str]) -> List[str]:
    """mkdocs takes exactly one command, so 'serve build' is a typo rather than a valid run."""
    return [argument for argument in argv if argument in COMMANDS][1:]


def main(argv: Sequence[str]) -> int:
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    superfluous = superfluous_commands(argv)
    if superfluous:
        error_print(f"Only one mkdocs command is allowed, got in addition: {', '.join(superfluous)}")
        return 1
    command, sync, mkdocs_arguments = split_arguments(argv)
    uv_path = get_uv_path()
    if sync and run_in_root([uv_path, "sync", *extra_arguments()]) != 0:
        error_print(f"Failed to install the {' and '.join(ROOT_EXTRAS)} dependencies of the root project.")
        return 1
    mkdocs_call = [uv_path, "run", "mkdocs", command, *COMMANDS[command], *mkdocs_arguments]
    return run_in_root(mkdocs_call, serving=command == "serve")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
