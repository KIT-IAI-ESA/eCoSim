from pathlib import Path
from typing import Any

import pytest
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_server.config.simulation_config import SimulationConfig
from tests.data.generate_connection_config import single_delay_file


def _loaded_start_value(
    directory: Path,
    start_value: Any,
    delay: int = 1,
) -> InterfaceValue:
    file = single_delay_file(directory=directory, delay=delay, start_value=start_value)
    config = SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)
    return config.logical_delays[0].logical_delay_connections[0].start_value


def _element_types(value: InterfaceValue) -> set[type]:
    if isinstance(value, list):
        return {element_type for element in value for element_type in _element_types(element)}
    return {type(value)}


def test_list_start_value_becomes_a_list_of_floats(tmp_path: Path) -> None:
    start_value = _loaded_start_value(directory=tmp_path, start_value=["1.5", 2])

    assert start_value == [1.5, 2.0]
    assert _element_types(start_value) == {float}


def test_nested_list_start_value_becomes_a_nested_list_of_floats(tmp_path: Path) -> None:
    start_value = _loaded_start_value(directory=tmp_path, start_value=[[1, 2, 3], [4, 5, "6"]])

    assert start_value == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    assert _element_types(start_value) == {float}


@pytest.mark.parametrize("delay", [0, -1])
def test_delay_shorter_than_one_step_fails_the_load(tmp_path: Path, delay: int) -> None:
    with pytest.raises(RuntimeError, match=f"at least 1 step.*{delay}"):
        _loaded_start_value(directory=tmp_path, start_value="1.0", delay=delay)
