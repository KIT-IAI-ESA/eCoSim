#!/usr/bin/env python3
"""Fail unless a version can be released: it looks like 1.0.0, is newer than the latest release tag
and than the version on main, and has no tag yet. prepare-release.yml runs it before it opens the
release pull request.

Usage: cd dev && python -m release.check_new_version 1.0.0
"""

import argparse
import sys

from config import REPO_ROOT, error_print
from release.release_common import ReleaseError, git_tags, is_valid_new_version_or_error, parse_version, project_versions


def check_newer_than_main(version: str, on_main: str) -> None:
    """A version merged to main but not released yet has no tag, so the tags alone do not see it."""
    new, current = parse_version(version), parse_version(on_main)
    if new is not None and current is not None and new <= current:
        raise ReleaseError(f"{version} is not newer than {on_main}, the version on main")


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Fail unless VERSION can be released.")
    parser.add_argument("version", help="the new version, e.g. 1.0.0")
    version = parser.parse_args(arguments).version
    try:
        is_valid_new_version_or_error(version=version, tags=git_tags())
        check_newer_than_main(version=version, on_main=project_versions(root=REPO_ROOT)["."])
    except ReleaseError as error:
        error_print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
