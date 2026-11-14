from pathlib import Path

import pytest
from ecosim_common.config.config_parser import ConfigParser, ConfigParserException


def test_a_section_keeps_the_case_of_its_keys(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[start_values]\nU_wall = 0.3\nzon5R1C.capMas.T = 291.15\n", encoding="utf-8")

    assert ConfigParser(file).get_section("start_values") == {"U_wall": "0.3", "zon5R1C.capMas.T": "291.15"}


def test_a_missing_section_has_no_keys(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[simulator]\nsimulator_name = house\n", encoding="utf-8")

    assert ConfigParser(file).get_section("start_values") == {}


def test_two_keys_that_differ_only_in_case_show_the_file_the_key_and_the_line(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[start_values]\nU_wall = 0.3\nu_wall = 0.4\n", encoding="utf-8")

    with pytest.raises(ConfigParserException) as error:
        ConfigParser(file)

    assert str(error.value) == f"{file} has the key u_wall twice in [start_values], the second time in line 3. Keys are not case-sensitive."


def test_the_keys_of_a_section_are_listed_as_the_getters_read_them(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[simulator]\nsimulator_name = house\nModelName = house\n", encoding="utf-8")

    assert ConfigParser(file).options("simulator") == ["simulator_name", "modelname"]


def test_a_missing_section_lists_no_keys(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[simulator]\nsimulator_name = house\n", encoding="utf-8")

    assert ConfigParser(file).options("fmu") == []


def test_a_missing_key_tells_its_section_and_key_apart_from_the_message(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[simulator]\nsimulator_name = house\n", encoding="utf-8")

    with pytest.raises(ConfigParserException) as error:
        ConfigParser(file).get_string("simulator", "model_name")

    assert (error.value.section, error.value.option) == ("simulator", "model_name")


def test_a_missing_section_tells_the_section_and_no_key_apart_from_the_message(tmp_path: Path) -> None:
    file = tmp_path / "config.ini"
    file.write_text("[Simulator]\nsimulator_name = house\n", encoding="utf-8")

    with pytest.raises(ConfigParserException) as error:
        ConfigParser(file).get_string("simulator", "simulator_name")

    assert (error.value.section, error.value.option) == ("simulator", None)
