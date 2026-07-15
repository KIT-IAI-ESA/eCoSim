from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ConnectedToData
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import SimulationConfig
from tests.tech.resource_utils import resource_path_file


def test_load() -> None:
    config = SimulationConfig.of_config_file_and_params(resource_path_file("simulation_bergwald.json"), 1221)
    # CLIENTS
    assert len(config.clients) == 5

    # CLIENTS[0]
    client0 = config.clients[0]
    assert client0.simulator_name == "Grid"
    assert client0.model_name == "Grid"
    assert len(client0.interfaces) == 8
    # CLIENTS[0].INTERFACE[0]
    interface0 = client0.interfaces[0]
    assert interface0.model_interface_id == ModelInterfaceId(model_name="Grid", interface="Pe_gen_B_1")
    assert interface0.name == "Pe_gen_B_1"
    assert interface0.type == InterfaceType.INPUT
    assert interface0.unit == ""
    assert interface0.required is False
    assert interface0.description == ""
    assert len(interface0.connected_to) == 1

    assert interface0.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId("B_1", ModelInterfaceId("B_1", "Pe_gen_B_1")),
            delay_path=[],
        ),
    ]
