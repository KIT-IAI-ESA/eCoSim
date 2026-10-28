from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.client.simulator_client import SimulatorClient

from integration_tests.clients.base.client_server_configs import (
    ClientMeasurementRecords,
    InputValueGenerator,
    client_simulator_config,
    create_driver_client_for,
    driver_simulator_config,
)
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import (
    SimpleTestServer,
    SimpleTestServerParameters,
    generate_simple_test_server,
)

START_DATE = datetime(2025, 1, 1)


@dataclass
class BaseSimulation:
    """A real server running the client under test, whose inputs are fed by a driver client."""

    server: SimpleTestServer
    client: SimulatorClient
    driver: SimpleTestClient

    @staticmethod
    def of(
        client: SimulatorClient,
        host: str,
        port: int,
        steps: int,
        input_value_generator: InputValueGenerator,
    ) -> BaseSimulation:
        interfaces: ClientInterfaceConfig = client._client_config.interfaces_config()  # noqa: SLF001
        protocol = client._client_config.communication_protocol()  # noqa: SLF001
        server = generate_simple_test_server(
            SimpleTestServerParameters(
                communication_protocol=protocol,
                host=host,
                port=port,
                steps=steps,
                simulation_start_date=START_DATE,
                clients=[driver_simulator_config(interfaces), client_simulator_config(client.client_id, interfaces)],
            ),
        )
        return BaseSimulation(
            server=server,
            client=client,
            driver=create_driver_client_for(protocol, host, port, interfaces, input_value_generator),
        )

    def run(self, timeout_in_seconds: float = 60) -> None:
        server_thread = threading.Thread(target=self.server.start, daemon=True)
        server_thread.start()
        self.client.start()
        self.driver.start()
        server_thread.join(timeout_in_seconds)
        assert not server_thread.is_alive(), f"The simulation did not finish within {timeout_in_seconds}s"

    def client_measurements(self) -> ClientMeasurementRecords:
        repository = self.server.measurement_repository(self.client.client_id)
        return {(entry.timestamp - START_DATE).total_seconds(): {value.name: value.value for value in entry.values} for entry in repository.all()}

    def _client_interfaces(self) -> ClientInterfaceConfig:
        return self.client._client_config.interfaces_config()  # noqa: SLF001

    def input_names(self) -> set[str]:
        return set(self._client_interfaces().input_interface_names())

    def output_names(self) -> set[str]:
        return {interface.name for interface in self._client_interfaces().interfaces} - self.input_names()

    def current_time(self) -> datetime:
        return START_DATE + timedelta(self.current_simulation_time())

    def current_simulation_time(self) -> float:
        return self.client._current_simulation_time  # noqa: SLF001
