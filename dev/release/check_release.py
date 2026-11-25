#!/usr/bin/env python3
"""Check that a version can be released from main. release.yml runs it before it builds.

Every package on main has this version, it looks like 1.0.0, is newer than the latest release tag and
has no tag yet, and none of the published packages has it on PyPI yet.

Usage: cd dev && python -m release.check_release 1.0.0 ecosim-common ecosim-server ...
"""

import argparse
import urllib.error
import urllib.request

import sys
from config import REPO_ROOT, error_print
from release.release_common import ReleaseError, git_tags, is_valid_new_version_or_error, project_versions


def check_version_on_main(version: str, versions: dict[str, str]) -> None:
    on_main = set(versions.values())
    if on_main != {version} and len(on_main) == 1:
        raise ReleaseError(f"main has {versions['.']}, not {version}")
    differing = [f"{project} has {project_version}" for project, project_version in versions.items() if project_version != version]
    if differing:
        raise ReleaseError(f"not every package on main has {version}: " + ", ".join(differing))


def is_on_pypi(package: str, version: str) -> bool:
    """Any answer of PyPI but 'not found' stops the release, rather than risking an upload."""
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/{package}/{version}/json".format(package=package, version=version), timeout=30):
            return True
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def check_not_on_pypi(packages: list[str], version: str) -> None:
    published = [package for package in packages if is_on_pypi(package=package, version=version)]
    if published:
        raise ReleaseError(
            f"{version} is on PyPI already for {', '.join(published)}; repeat a failed release with 'Re-run failed jobs' of its run",
        )


def check_release(version: str, packages: list[str]) -> None:
    check_version_on_main(version=version, versions=project_versions(root=REPO_ROOT))
    is_valid_new_version_or_error(version=version, tags=git_tags())
    check_not_on_pypi(packages=packages, version=version)


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check that VERSION can be released from main.")
    parser.add_argument("version", help="the version to release, e.g. 1.0.0")
    parser.add_argument("packages", nargs="+", help="the published packages, PACKAGES of release.yml")
    options = parser.parse_args(arguments)
    try:
        check_release(version=options.version, packages=options.packages)
    except ReleaseError as error:
        error_print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
