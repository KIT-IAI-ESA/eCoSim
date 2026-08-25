import threading
from datetime import datetime
from typing import Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServerParameters, generate_simple_test_server


def test_client_server_single(communication_protocol: CommunicationProtocol) -> None:
    server_host = "localhost"
    server_port = 47189
    steps = 100
    step_size_in_ms = 2_500
    simulation_start_date: datetime = datetime(
        year=2025,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host=server_host,
            port=server_port,
            steps=steps,
            step_size_in_ms=step_size_in_ms,
            simulation_start_date=simulation_start_date,
        ),
    )
    client = SimpleTestClient.generate(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        on_simulation_step_return=lambda _self, received_inputs, steps: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value,
                ),
            ],
        ),
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client.start()

    server_thread.join(120)
    server.print_measurement_statistics()

    client_measurement_repository = server.measurement_repository(client_id=client.client_id)

    if not isinstance(client_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() == values[0].value
        return (timestamp - simulation_start_date).total_seconds() == values[0].value

    (client_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_records))
