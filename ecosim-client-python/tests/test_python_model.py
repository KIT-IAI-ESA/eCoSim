import re
from decimal import Decimal
from typing import Any

import pytest
from ecosim_test_common.test_data.python_models import (
    ClockModel,
    DecoratedClockModel,
    DividingByZeroModel,
    DoublingModel,
    EchoModel,
    KeywordOnlyClockModel,
    NumpyLikeArray,
    NumpyLikeNumber,
    PositionalOnlyClockModel,
    ScriptedOutputsModel,
)

from ecosim_client_python.python_model import PythonModel


def _initialized_model_returning(start_outputs: Any) -> PythonModel:
    model = PythonModel.of_object(model=ScriptedOutputsModel(start_outputs=start_outputs), model_reference="room:Room")
    model.initialize()
    return model


def test_do_step_gets_the_simulation_time_and_the_step_size_when_it_has_parameters_for_them() -> None:
    model = PythonModel.of_object(model=ClockModel(), model_reference="room:Room")
    model.initialize()

    model.do_step(current_simulation_time=1800.0, step_size_in_seconds=900.0)

    assert [model.output(name="time"), model.output(name="step_size")] == [1800.0, 900.0]


@pytest.mark.parametrize("model", [KeywordOnlyClockModel(), DecoratedClockModel()], ids=["keyword-only", "decorated"])
def test_do_step_gets_the_simulation_time_also_as_a_keyword_only_parameter_or_behind_a_decorator(model: Any) -> None:
    python_model = PythonModel.of_object(model=model, model_reference="room:Room")
    python_model.initialize()

    python_model.do_step(current_simulation_time=1800.0, step_size_in_seconds=900.0)

    assert python_model.output(name="time") == 1800.0


def test_a_positional_only_time_parameter_is_not_passed_and_keeps_its_default() -> None:
    model = PythonModel.of_object(model=PositionalOnlyClockModel(), model_reference="room:Room")
    model.initialize()

    model.do_step(current_simulation_time=1800.0, step_size_in_seconds=900.0)

    assert model.output(name="time") == -1.0


def test_do_step_of_a_pyro5_model_gets_only_the_inputs() -> None:
    model = PythonModel.of_object(model=DoublingModel(), model_reference="room:Room")
    model.initialize()
    model.set_input(name="u", value=1.5)

    model.do_step(current_simulation_time=0.0, step_size_in_seconds=1.0)

    assert model.output(name="y") == 3.0


def test_a_model_that_changes_value_dict_does_not_change_the_inputs_of_the_next_step() -> None:
    model = PythonModel.of_object(model=EchoModel(), model_reference="room:Room")
    model.initialize()
    model.set_input(name="u", value=1.5)
    model.do_step(current_simulation_time=0.0, step_size_in_seconds=1.0)

    model.do_step(current_simulation_time=1.0, step_size_in_seconds=1.0)

    assert model.output(name="y") == 1.5


def test_a_model_without_the_three_methods_is_rejected_before_the_run() -> None:
    with pytest.raises(TypeError, match=re.escape("room:Room has no initialize() and no do_step() and no clear()")):
        PythonModel.of_object(model=object(), model_reference="room:Room")


def test_integer_boolean_and_other_number_outputs_become_float() -> None:
    model = _initialized_model_returning(start_outputs={"count": 3, "is_on": True, "share": Decimal("0.25")})

    outputs = [model.output(name=name) for name in ("count", "is_on", "share")]

    assert outputs == [3.0, 1.0, 0.25]
    assert [type(output) for output in outputs] == [float, float, float]


def test_every_number_in_a_list_output_becomes_a_float() -> None:
    model = _initialized_model_returning(start_outputs={"temperatures": [NumpyLikeNumber(value=1.5), 2, True]})

    temperatures = model.output(name="temperatures")

    assert isinstance(temperatures, list)
    assert [(temperature, type(temperature)) for temperature in temperatures] == [(1.5, float), (2.0, float), (1.0, float)]


def test_a_number_in_a_matrix_output_becomes_a_float() -> None:
    model = _initialized_model_returning(start_outputs={"temperatures": [[NumpyLikeNumber(value=1.5)], [NumpyLikeNumber(value=2.0)]]})

    temperatures: Any = model.output(name="temperatures")

    assert [[(temperature, type(temperature)) for temperature in row] for row in temperatures] == [[(1.5, float)], [(2.0, float)]]


@pytest.mark.parametrize("value", [None, "warm", "21.5", {"value": 21.0}, NumpyLikeArray(value=21.0)])
def test_an_output_that_is_not_a_number_is_rejected(value: Any) -> None:
    model = _initialized_model_returning(start_outputs={"temperature": value})

    with pytest.raises(TypeError, match=re.escape(f"room:Room.initialize() returned {value!r} for the output temperature")):
        model.output(name="temperature")


@pytest.mark.parametrize("value", [None, "warm", (21.0, 22.0), NumpyLikeArray(value=22.0)])
def test_a_value_in_a_list_output_that_is_not_a_number_is_rejected(value: Any) -> None:
    model = _initialized_model_returning(start_outputs={"temperature": [21.0, value]})

    with pytest.raises(TypeError, match=re.escape(f"room:Room.initialize() returned a list with {value!r} for the output temperature")):
        model.output(name="temperature")


def test_a_missing_output_lists_the_outputs_the_model_returned() -> None:
    model = _initialized_model_returning(start_outputs={"humidity": 0.5})

    with pytest.raises(ValueError, match=re.escape("room:Room.initialize() returned no value for the output temperature. It returned: humidity")):
        model.output(name="temperature")


def test_a_missing_output_after_a_step_shows_do_step() -> None:
    scripted_model = ScriptedOutputsModel(start_outputs={"temperature": 20.0}, step_outputs={"humidity": 0.5})
    model = PythonModel.of_object(model=scripted_model, model_reference="room:Room")
    model.initialize()
    model.do_step(current_simulation_time=0.0, step_size_in_seconds=1.0)

    with pytest.raises(ValueError, match=re.escape("room:Room.do_step() returned no value for the output temperature. It returned: humidity")):
        model.output(name="temperature")


def test_an_error_in_initialize_shows_the_model_and_keeps_the_error_of_the_model_code() -> None:
    model = PythonModel.of_object(model=DividingByZeroModel(), model_reference="room:Room")

    with pytest.raises(RuntimeError, match=re.escape("The model room:Room failed in initialize(): division by zero")) as error_info:
        model.initialize()

    assert isinstance(error_info.value.__cause__, ZeroDivisionError)


def test_do_step_without_a_dictionary_says_what_it_has_to_return() -> None:
    model = _initialized_model_returning(start_outputs={"temperature": 20.0})

    with pytest.raises(TypeError, match=re.escape("room:Room.do_step() returned None. It has to return a dictionary with every output")):
        model.do_step(current_simulation_time=0.0, step_size_in_seconds=1.0)
