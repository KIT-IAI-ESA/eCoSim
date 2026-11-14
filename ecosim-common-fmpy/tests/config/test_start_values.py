import logging
import re
from pathlib import Path

import pytest
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.start_values import StartValues
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path, resource_path_file

_SUB1 = resource_path_file("fmu_v2/test_fmus/Sub1_Linux.fmu")
_HOUSE = resource_path_file("fmu_v2/models/house/linux/house.fmu")


def _start_values(fmu_file: Path, texts: dict[str, str], input_names: list[str] | None = None) -> StartValues:
    return StartValues.of_texts(
        texts=texts,
        model_description=read_model_description(file=fmu_file),
        input_names=input_names or [],
        fmu_file=fmu_file,
    )


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "StartValues" and record.levelno == logging.WARNING]


def test_the_values_get_the_type_of_their_variable() -> None:
    texts = {"Float64_tunable_parameter": "2.5", "Int32_input": "-3", "Boolean_input": "yes"}

    start_values = _start_values(fmu_file=fmu2_model_path(), texts=texts)

    assert [(type(start_value.value), start_value.value) for start_value in start_values.values] == [(float, 2.5), (int, -3), (bool, True)]


@pytest.mark.parametrize(
    ("fmu_file", "name", "reason"),
    [
        (_SUB1, "springDamper.s_nominal", "a constant of the FMU cannot be changed"),
        (fmu2_model_path(), "Float64_continuous_output", "a value calculated by the FMU cannot be set"),
        (fmu2_model_path(), "time", "the simulation time cannot be set"),
        (fmu3_model_path(), "n", "eCoSim cannot change a structural parameter"),
        (fmu2_model_path(), "Float64_continuous_input", "an input in the .fmc file gets a new value every step"),
        (fmu3_model_path(), "x0", "an array, but [start_values] takes single values only"),
        (fmu2_model_path(), "String_input", "[start_values] does not support the type String"),
    ],
)
def test_a_variable_that_cannot_take_a_start_value_is_rejected(fmu_file: Path, name: str, reason: str) -> None:
    with pytest.raises(ValueError, match=re.escape(f"{name}: {reason}")):
        _start_values(fmu_file=fmu_file, texts={name: "1"}, input_names=["Float64_continuous_input"])


@pytest.mark.parametrize(
    ("name", "text", "reason"),
    [
        ("Float64_tunable_parameter", "abc", "'abc' is not a number"),
        ("Float64_tunable_parameter", "2.5  # in m", "'2.5  # in m' is not a number. Write a comment on its own line"),
        ("Float64_tunable_parameter", "nan", "'nan' is not a finite number"),
        ("Float64_tunable_parameter", "", "no value after the ="),
        ("Int32_input", "2.5", "'2.5' is not a whole number"),
        ("Int32_input", "3000000000", "3000000000 does not fit into Integer (-2147483648 to 2147483647)"),
        ("Boolean_input", "maybe", "'maybe' is not true or false"),
    ],
)
def test_a_value_that_does_not_fit_its_variable_is_rejected(name: str, text: str, reason: str) -> None:
    with pytest.raises(ValueError, match=re.escape(f"{name}: {reason}")):
        _start_values(fmu_file=fmu2_model_path(), texts={name: text})


@pytest.mark.parametrize(
    ("fmu_file", "name", "text", "line", "passed_limit"),
    [
        pytest.param(_SUB1, "mass.m", "-1", "mass.m = -1.0 kg", "below the minimum of the FMU, 0.0 kg", id="minimum of the declared type"),
        pytest.param(
            _HOUSE,
            "vetnilation_valve_control_signal",
            "2",
            "vetnilation_valve_control_signal = 2.0",
            "above the maximum of the FMU, 1.0",
            id="maximum of the variable",
        ),
    ],
)
def test_a_value_outside_the_minimum_or_the_maximum_is_taken_with_a_warning(
    caplog: pytest.LogCaptureFixture,
    fmu_file: Path,
    name: str,
    text: str,
    line: str,
    passed_limit: str,
) -> None:
    caplog.set_level(logging.WARNING, logger="StartValues")

    start_values = _start_values(fmu_file=fmu_file, texts={name: text})

    assert start_values.as_lines() == [line]
    assert _warnings(caplog=caplog) == [f"The start value {line} is {passed_limit}. The client sets it anyway."]


def test_a_value_within_the_minimum_and_the_maximum_gets_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="StartValues")

    _start_values(fmu_file=_HOUSE, texts={"vetnilation_valve_control_signal": "0.5"})

    assert _warnings(caplog=caplog) == []


def test_a_variable_with_initial_approx_takes_a_start_value() -> None:
    start_values = _start_values(fmu_file=resource_path_file("hpc/modules/house/house.fmu"), texts={"traceSubstance_room.C": "0.5"})

    assert start_values.as_lines() == ["traceSubstance_room.C = 0.5"]


def test_an_unknown_name_gets_the_closest_variable_as_a_hint() -> None:
    with pytest.raises(ValueError, match=re.escape("Float64_tunable_paramter: not a variable of the FMU. Did you mean Float64_tunable_parameter?")):
        _start_values(fmu_file=fmu2_model_path(), texts={"Float64_tunable_paramter": "1"})


def test_every_problem_is_listed_at_once() -> None:
    texts = {"unknown": "1", "Float64_tunable_parameter": "abc", "Float64_fixed_parameter": "1", "time": "0"}

    with pytest.raises(ValueError) as error:
        _start_values(fmu_file=fmu2_model_path(), texts=texts)

    assert [line.split(":")[0].strip() for line in str(error.value).splitlines()[1:]] == ["unknown", "Float64_tunable_parameter", "time"]


def test_a_check_gets_the_same_problems_as_a_list() -> None:
    texts = {"Float64_tunable_parameter": "abc", "Float64_fixed_parameter": "1"}

    problems = StartValues.problems_of(texts=texts, model_description=read_model_description(file=fmu2_model_path()), input_names=[])

    assert problems == ["Float64_tunable_parameter: 'abc' is not a number"]


@pytest.mark.parametrize("section", ["Start_Values", "start_value", "start values", "startvalues"])
def test_a_misspelled_section_name_is_rejected(tmp_path: Path, section: str) -> None:
    file = tmp_path / "preferences.ini"
    file.write_text(f"[{section}]\nU_wall = 0.3\n", encoding="utf-8")

    with pytest.raises(ValueError, match=re.escape(f"has a section [{section}]. Did you mean [start_values]?")):
        StartValues.texts_of(config_parser=ConfigParser(file))


def test_a_section_with_another_name_is_left_alone(tmp_path: Path) -> None:
    file = tmp_path / "preferences.ini"
    file.write_text("[parameters]\nU_wall = 0.3\n", encoding="utf-8")

    assert StartValues.texts_of(config_parser=ConfigParser(file)) == {}
