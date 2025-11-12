import threading
from datetime import datetime, timedelta

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import (
    generate_simple_test_server,
)
from integration_tests.tech.db.measurement_repository_in_memory import (
    MeasurementRepositoryInMemory,
)


def test_client_server_batch_steps() -> None:
    server_host = "localhost"
    server_port = 47189
    steps = 10
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
        host=server_host,
        port=server_port,
        steps=steps,
        step_size_in_ms=step_size_in_ms,
        simulation_start_date=simulation_start_date,
        restore_simulation_run=True,
    )
    client = SimpleTestClient.generate(
        server_host=server_host,
        server_port=server_port,
        on_simulation_step_return=lambda _self,
        received_inputs,
        steps: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value,
                ),
            ],
        ),
    )
    step_size_in_seconds = step_size_in_ms / 1000
    client_measurement_repository = server.repositories.measurement_repository(
        client_id=client._client_config.client_id(),
    )
    for i in range(5):
        entry_date = simulation_start_date + timedelta(seconds=i * step_size_in_seconds)
        client_measurement_repository.add(
            (
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=i + step_size_in_seconds,
                ),
            ),
            entry_date,
        )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client.start()

    server_thread.join()

    client_measurement_repository = server.repositories.measurement_repository(
        client_id=client._client_config.client_id(),
    )
    (ProtocolInterfaceValue(name="TestInterface", value=2.5),)

    if not isinstance(client_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    (
        client_measurement_repository.assert_entry_count(steps).assert_for_each_record(
            lambda timestamp, values: (
                timestamp - simulation_start_date
            ).total_seconds()
            + step_size_in_seconds
            == values[0].value,
        )
    )
