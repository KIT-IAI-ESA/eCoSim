from typing import Any

import pytest
from ecosim_common.config.model_interface_server import ConnectedToData, ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId


def _load_input(fields: dict[str, Any]) -> ModelInterfaceServer:
    return ModelInterfaceServer.of_config_json(
        simulator_name="house",
        model_name="house",
        raw_interface={"name": "T_out", "type": "Input", **fields},
        raw_simulators=[{"name": "weather", "model": "weather"}, {"name": "house", "model": "house"}],
    )


@pytest.mark.parametrize("required", [True, False])
def test_required_accepts_a_json_boolean(required: bool) -> None:
    assert _load_input(fields={"required": required}).required is required


@pytest.mark.parametrize("simulator", [0, "0"], ids=["number", "text"])
def test_the_first_simulator_can_be_given_as_a_number_or_as_text(simulator: int | str) -> None:
    interface = _load_input(fields={"connected_to": [{"simulator": simulator, "interface": "T_out"}]})

    weather_output = SimulatorInterfaceId(simulator_name="weather", model_interface_id=ModelInterfaceId(model_name="weather", interface="T_out"))
    assert interface.connected_to == [ConnectedToData(simulator_interface_id=weather_output, delay_path=[])]
