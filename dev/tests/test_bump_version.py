import shutil
import tomllib
from itertools import chain
from pathlib import Path
from typing import Any

from bump_version import ALL_PROJECTS, ECOSIM_PROJECTS, pin_internal_packages, read_pyproject, set_version
from config import REPO_ROOT

NEW_VERSION = "9.9.9"


def copy_pyproject_files(target: Path) -> None:
    for project in ALL_PROJECTS:
        (target / project).mkdir(parents=True, exist_ok=True)
        shutil.copy(src=REPO_ROOT / project / "pyproject.toml", dst=target / project / "pyproject.toml")


def project_table(project: Path) -> dict[str, Any]:
    return dict(tomllib.loads(read_pyproject(project))["project"])


def internal_pins(project: Path) -> list[str]:
    table = project_table(project)
    requirements = chain(table.get("dependencies", []), *table.get("optional-dependencies", {}).values())
    # "ecosim==", "ecosim-common==" and "ecosim-server[pandas]=="
    return [requirement for requirement in requirements if requirement.startswith("ecosim")]


def test_sets_every_version_field_and_internal_pin(tmp_path: Path) -> None:
    copy_pyproject_files(target=tmp_path)

    set_version(root=tmp_path, version=NEW_VERSION)

    assert {project_table(tmp_path / project)["version"] for project in ECOSIM_PROJECTS} == {NEW_VERSION}
    pins = [pin for project in ALL_PROJECTS for pin in internal_pins(tmp_path / project)]
    assert {pin.partition("==")[2] for pin in pins} == {NEW_VERSION}


def test_changes_nothing_but_the_version_fields_and_internal_pins(tmp_path: Path) -> None:
    copy_pyproject_files(target=tmp_path)
    current_version = project_table(tmp_path)["version"]
    before = {project: read_pyproject(tmp_path / project) for project in ALL_PROJECTS}

    set_version(root=tmp_path, version=NEW_VERSION)

    for project in ALL_PROJECTS:
        assert read_pyproject(tmp_path / project).replace(NEW_VERSION, current_version) == before[project]


def test_leaves_other_packages_pinned_to_the_same_version_alone() -> None:
    pyproject = '"ecosim-common==0.14.0",\n"ecosim-common-fmpy==0.14.0",\n"ruff==0.14.0",\n'

    pinned = pin_internal_packages(pyproject=pyproject, packages=["ecosim-common"], version=NEW_VERSION)

    assert pinned == '"ecosim-common==9.9.9",\n"ecosim-common-fmpy==0.14.0",\n"ruff==0.14.0",\n'


def test_a_pin_with_extras_keeps_them() -> None:
    pinned = pin_internal_packages(pyproject='"ecosim-server[pandas]==0.14.0",\n', packages=["ecosim-server"], version=NEW_VERSION)

    assert pinned == '"ecosim-server[pandas]==9.9.9",\n'
