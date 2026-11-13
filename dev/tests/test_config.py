from pathlib import Path
from typing import Any

import pytest
import yaml

from config import REPO_ROOT, SUBPROJECTS, pytest_command, write_or_check
from run_unit_tests import all_projects_apart_integration_tests


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_write_or_check_writes_the_file(tmp_path: Path) -> None:
    page = tmp_path / "page.md"

    assert write_or_check(page, "new", check=False) == 0
    assert page.read_text(encoding="utf-8") == "new"


def test_write_or_check_accepts_an_up_to_date_file(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text("same", encoding="utf-8")

    assert write_or_check(page, "same", check=True) == 0


def test_write_or_check_reports_an_out_of_date_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    page = tmp_path / "page.md"
    page.write_text("old", encoding="utf-8")

    assert write_or_check(page, "new", check=True) == 1
    assert page.read_text(encoding="utf-8") == "old"
    assert "page.md is out of date" in capsys.readouterr().err


def test_pytest_command_selects_the_marker_and_forwards_the_arguments() -> None:
    assert pytest_command(marker="integration", pytest_arguments=["-k", "restore"])[1:] == ["run", "pytest", "-m", "integration", "-k", "restore"]


def test_no_subproject_is_left_out_of_the_unit_tests_in_ci() -> None:
    workflow = read_yaml(REPO_ROOT / ".github" / "workflows" / "tests.yml")
    matrix_projects = workflow["jobs"]["unit-tests"]["strategy"]["matrix"]["project"]

    assert sorted(matrix_projects) == sorted(path.name for path in all_projects_apart_integration_tests())


def test_every_subproject_is_type_checked_by_its_own_mypy_hook() -> None:
    hooks = [hook for repository in read_yaml(REPO_ROOT / ".pre-commit-config.yaml")["repos"] for hook in repository["hooks"]]
    subproject_hooks = {hook["entry"]: hook["files"] for hook in hooks if hook.get("entry", "").startswith("python dev/run_mypy.py ")}

    assert subproject_hooks == {f"python dev/run_mypy.py {path.name}": f"^{path.name}/" for path, _ in SUBPROJECTS}
