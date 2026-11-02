from pathlib import Path

import pytest
from ecosim_common.config.config_parser import ConfigParser


@pytest.mark.parametrize("value", ["100%", "pass%word", "pass%41word", "%%", "%(server)s", "%(unknown)s", "a@b/c#d%e"])
def test_percent_signs_are_read_literally(
    tmp_path: Path,
    value: str,
) -> None:
    file = tmp_path / "config.ini"
    file.write_text(f"[database]\nserver=localhost\npassword={value}\n", encoding="utf-8")

    assert ConfigParser(file).get_string("database", "password") == value
