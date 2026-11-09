from __future__ import annotations

from dataclasses import dataclass

from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.config_parser import ConfigParser
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources.simulations.house_simulation_data import ExpectedResultEntry, HouseSimulationData

from integration_tests.test_data.server_client.simple_test_server import (
    SERVER_FINISH_TIMEOUT_IN_SECONDS,
    SimpleTestServer,
    SimpleTestServerParameters,
    generate_simple_test_server,
)


@dataclass
class HouseSimulation:
    """Runs the houses scenario of 'HouseSimulationData' on a real server: one FMU2 client per module."""

    server: SimpleTestServer
    clients: dict[str, FMU2Client]

    @staticmethod
    def of(
        communication_protocol: CommunicationProtocol,
        host: str,
        port: int,
        steps: int = HouseSimulationData.STEPS,
    ) -> HouseSimulation:
        simulation_config = SimulationConfig.of_config_file_and_params(
            simulation_config_file=HouseSimulationData.SIMULATION_CONFIG_FILE,
            steps=steps,
        )
        server = generate_simple_test_server(
            SimpleTestServerParameters.of_simulation_config(
                communication_protocol=communication_protocol,
                host=host,
                port=port,
                simulation_config=simulation_config,
            ),
        )
        override = ClientConfigOverride(
            server_host=host,
            server_port=port,
            communication_protocol=communication_protocol,
        )
        clients = {
            module: FMU2Client.create(
                config_parser=ConfigParser(HouseSimulationData.client_config_file(module)),
                config_override=override,
            )
            for module in HouseSimulationData.MODULES
        }
        return HouseSimulation(server=server, clients=clients)

    def run(self, timeout_in_seconds: float = SERVER_FINISH_TIMEOUT_IN_SECONDS) -> None:
        self.server.start_in_thread()
        self.server.wait_until_listening()
        for client in self.clients.values():
            client.start()
        self.server.assert_finishing_in_time(timeout_in_seconds=timeout_in_seconds)

    def recorded_rows(self, module: str) -> list[ExpectedResultEntry]:
        entries = sorted(self.server.measurement_repository(self.clients[module].client_id).all(), key=lambda entry: entry.timestamp)
        return [{value.name.lower(): value.value for value in entry.values} for entry in entries]
