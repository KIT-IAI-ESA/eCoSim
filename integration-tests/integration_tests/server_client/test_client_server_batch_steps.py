import threading
from datetime import datetime, timedelta

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.config.interface_type import InterfaceType

from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import (
    generate_simple_test_server,
)
from integration_tests.tech.db.measurement_repository_in_memory import (
    MeasurementRepositoryInMemory,
)
from integration_tests.test_data.test_client_data import TestClientData


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

    client_data_1 = TestClientData(
        simulator_name="Simulator_1",
        model_name="Model_1",
        interfaces=[],
    )
    client_1_input_interface = client_data_1.add_interface(
        interface_name="Interface_Input_1",
        unit="float64_matrix",
        interface_type=InterfaceType.INPUT,
    )
    client_data_1.add_interface(
        interface_name="Interface_Output_1",
        unit="float64_matrix",
        interface_type=InterfaceType.OUTPUT,
    )

    client_data_2 = TestClientData(
        simulator_name="Simulator_2",
        model_name="Model_2",
        interfaces=[],
    )
    client_data_2.add_interface(
        interface_name="Interface_Output_2",
        unit="float64_matrix",
        interface_type=InterfaceType.OUTPUT,
        connected_interface=client_1_input_interface,
    )

    server = generate_simple_test_server(
        host=server_host,
        port=server_port,
        steps=steps,
        step_size_in_ms=step_size_in_ms,
        simulation_start_date=simulation_start_date,
        restore_simulation_run=True,
        clients=[
            client_data_1.to_client_simulator_config(),
            client_data_2.to_client_simulator_config(),
        ],
    )

    client_1 = SimpleTestClient.of_test_data(
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_1,
        on_simulation_step_return=lambda _self,
        received_inputs,
        steps: ClientSimStepData(
            interface_values=[
                client_data_1.interface_protocol_value_of(
                    "Interface_Output_1",
                    _self.accumulated_step_sizes_in_seconds.value,
                ),
            ],
        ),
    )
    client_2 = SimpleTestClient.of_test_data(
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_2,
        on_simulation_step_return=lambda _self,
        received_inputs,
        steps: ClientSimStepData(
            interface_values=[
                client_data_2.interface_protocol_value_of(
                    "Interface_Output_2",
                    -_self.accumulated_step_sizes_in_seconds.value,
                ),
            ],
        ),
    )
    step_size_in_seconds = step_size_in_ms / 1000
    client_measurement_repository = server.repositories.measurement_repository(
        client_id=client_1.client_id,
    )
    for i in range(5):
        entry_date = simulation_start_date + timedelta(seconds=i * step_size_in_seconds)
        client_measurement_repository.add(
            values=(
                client_data_1.interface_protocol_value_of(
                    interface_name="Interface_Output_1",
                    value=i * step_size_in_seconds,
                ),
            ),
            timestamp=entry_date,
        )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client_1.start()
    client_2.start()

    server_thread.join(timeout=4)

    client_measurement_repository = server.repositories.measurement_repository(
        client_id=client_1._client_config.client_id(),
    )

    if not isinstance(client_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    client_measurement_repository.assert_entry_count(steps).assert_for_each_record(
        lambda timestamp, values: (timestamp - simulation_start_date).total_seconds()
        + step_size_in_seconds
        == values[0].value,
    )
