import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.executing_platform import ExecutingPlatform
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData

from integration_tests.server_client.house_simulation.house_simulation import HouseSimulation


@pytest.mark.skipif(ExecutingPlatform.current() not in HouseSimulationData.PLATFORMS, reason="There are only linux and windows builds of the FMUs")
def test_the_house_simulation_reproduces_the_recorded_results(communication_protocol: CommunicationProtocol) -> None:
    simulation = HouseSimulation.of(communication_protocol=communication_protocol, host="localhost", port=get_free_port())

    simulation.run()

    for module in HouseSimulationData.MODULES:
        recorded, expected = simulation.recorded_rows(module), HouseSimulationData.expected_rows(module)
        assert len(recorded) == HouseSimulationData.STEPS, f"{module}: {len(recorded)} steps recorded"
        for step, (recorded_row, expected_row) in enumerate(zip(recorded, expected, strict=True), start=1):
            assert recorded_row == pytest.approx(expected_row), f"{module}, step {step}"
