from pathlib import Path

import pytest
from ecosim_common.tech.json.read_json_file import read_json_file


def test_json_that_cannot_be_read_shows_the_file_the_line_and_the_column(tmp_path: Path) -> None:
    file = tmp_path / "simulation.json"
    file.write_text('{\n  "setup": {}\n  "simulators": []\n}', encoding="utf-8")

    with pytest.raises(ValueError) as error_info:
        read_json_file(file=file)

    assert str(error_info.value) == f"{file} is not valid JSON: Expecting ',' delimiter in line 3, column 3."


def test_a_file_in_another_encoding_shows_the_file_the_line_and_utf_8(tmp_path: Path) -> None:
    file = tmp_path / "house.fmc"
    file.write_bytes('{\n  "outputs": [{"name": "T_indoor", "unit": "°C"}]\n}'.encode("cp1252"))

    with pytest.raises(ValueError) as error_info:
        read_json_file(file=file)

    assert str(error_info.value) == f"{file} is not saved as UTF-8: line 2 has a character in another encoding. Save the file as UTF-8."


def test_a_missing_file_shows_its_path(tmp_path: Path) -> None:
    file = tmp_path / "simulaton.json"

    with pytest.raises(FileNotFoundError) as error_info:
        read_json_file(file=file)

    assert error_info.value.filename == str(file)


def test_a_file_without_a_json_object_is_refused(tmp_path: Path) -> None:
    file = tmp_path / "simulation.json"
    file.write_text('[{"name": "house"}]', encoding="utf-8")

    with pytest.raises(ValueError) as error_info:
        read_json_file(file=file)

    assert str(error_info.value) == f"{file} has to contain a JSON object in {{ }}."
