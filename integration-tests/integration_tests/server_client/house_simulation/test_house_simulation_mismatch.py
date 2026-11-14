import json
from pathlib import Path

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.bounded_wait import finishes_in_time
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData

from integration_tests.server_client.house_simulation.house_simulation import HouseSimulation


def _with_a_misspelt_house_input(directory: Path) -> Path:
    config = json.loads(HouseSimulationData.SIMULATION_CONFIG_FILE.read_text(encoding="utf-8"))
    house = next(simulator for simulator in config["simulators"] if simulator["name"] == "house")
    misspelt_input = next(interface for interface in house["interfaces"] if interface["name"] == "T_out")
    # not required, since the server turns a client away before the start if it lacks a required interface
    misspelt_input.update({"name": "T_outt", "required": "false"})
    file = directory / "simulation.json"
    file.write_text(json.dumps(config), encoding="utf-8")
    return file


@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()
def test_an_input_the_house_fmu_lacks_ends_the_run_at_the_start(
    communication_protocol: CommunicationProtocol,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    simulation = HouseSimulation.of(
        communication_protocol=communication_protocol,
        host="localhost",
        port=get_free_port(),
        simulation_config_file=_with_a_misspelt_house_input(tmp_path),
    )
    server_run = simulation.server.start_in_thread()
    simulation.server.wait_until_listening()
    for client in simulation.clients.values():
        client.start()

    # a step waits 30 s for an answer, the check at the start ends the run long before
    server_run.assert_ends_within(timeout_in_seconds=15)
    assert "Lost client house#house while waiting for all clients to start their simulation" in str(server_run.error)
    assert finishes_in_time(blocking_call=simulation.clients["house"].wait_until_finished)
    assert "house#house did not start the simulation. The error above says why." in caplog.messages
