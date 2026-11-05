from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData

from integration_tests.server_client.house_simulation.house_simulation import HouseSimulation
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer

STEPS = 1000
TIMEOUT_IN_SECONDS = 600


def run_long_running_simulation_for_performance(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    simulation = HouseSimulation.of(communication_protocol=communication_protocol, host="localhost", port=get_free_port(), steps=STEPS)
    simulation.run(timeout_in_seconds=TIMEOUT_IN_SECONDS)
    for module in HouseSimulationData.MODULES:
        assert len(simulation.recorded_rows(module)) == STEPS, module
    return simulation.server
