import sys

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData

from integration_tests.server_client.house_simulation.house_simulation import HouseSimulation


@pytest.mark.skipif(sys.platform != "linux", reason="The FMUs only contain linux64 binaries")
def test_the_house_simulation_reproduces_the_recorded_results(communication_protocol: CommunicationProtocol) -> None:
    simulation = HouseSimulation.of(communication_protocol, host="localhost", port=38412)

    simulation.run()

    for module in HouseSimulationData.MODULES:
        recorded, expected = simulation.recorded_rows(module), HouseSimulationData.expected_rows(module)
        assert len(recorded) == HouseSimulationData.STEPS, f"{module}: {len(recorded)} steps recorded"
        for step, (recorded_row, expected_row) in enumerate(zip(recorded, expected), start=1):
            assert recorded_row == pytest.approx(expected_row), f"{module}, step {step}"
