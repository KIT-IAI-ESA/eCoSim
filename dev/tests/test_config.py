from pathlib import Path

import pytest

from config import write_or_check


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
