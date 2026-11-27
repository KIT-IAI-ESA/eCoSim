import re
import subprocess
import tomllib
from pathlib import Path

from config import REPO_ROOT, SUBPROJECTS

ECOSIM_PROJECTS = [Path("."), *(path.relative_to(REPO_ROOT) for path, _ in SUBPROJECTS)]
RELEASE_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class ReleaseError(Exception):
    pass


def read_pyproject(project: Path) -> str:
    return (project / "pyproject.toml").read_text(encoding="utf-8")


def project_versions(root: Path) -> dict[str, str]:
    return {str(project): str(tomllib.loads(read_pyproject(root / project))["project"]["version"]) for project in ECOSIM_PROJECTS}


def parse_version(version: str) -> tuple[int, ...] | None:
    match = RELEASE_VERSION.match(version)
    return tuple(int(part) for part in match.groups()) if match else None


def latest_release(tags: list[str]) -> tuple[int, ...] | None:
    released = [version for tag in tags if tag.startswith("v") and (version := parse_version(tag[1:]))]
    return max(released, default=None)


def is_valid_new_version_or_error(version: str, tags: list[str]) -> None:
    """
    Checks if the new version does not exist yet and is actually newer than the latest version.
    Otherwise, it raises an error.
    """
    new = parse_version(version)
    if new is None:
        raise ReleaseError(f"'{version}' is not a version like 1.0.0")
    if f"v{version}" in tags:
        raise ReleaseError(f"the tag v{version} exists already")
    latest = latest_release(tags=tags)
    if latest is not None and new <= latest:
        raise ReleaseError(f"{version} is not newer than {'.'.join(map(str, latest))}, the latest release")


def git_tags() -> list[str]:
    return subprocess.run(["git", "tag", "--list"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.split()
