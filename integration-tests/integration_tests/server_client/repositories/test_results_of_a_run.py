from datetime import datetime, timezone

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.simulation.state.simulation_state import SimulationState
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServerParameters, generate_simple_test_server
from integration_tests.test_data.test_client_data import TestClientData

STEPS = 5
STEP_SIZE_IN_MS = 2_500
OUTPUT_INTERFACE = "Interface_Output"


def test_a_stored_run_reads_back_as_one_table(database_config: DatabaseConfig, communication_protocol: CommunicationProtocol) -> None:
    client_data = TestClientData.with_output(
        simulator_name=f"ResultsSimulator_{database_config.type.value}_{communication_protocol.name}",
        model_name="ResultsModel",
        output_name=OUTPUT_INTERFACE,
    )
    server_port = get_free_port()
    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host="localhost",
            port=server_port,
            steps=STEPS,
            step_size_in_ms=STEP_SIZE_IN_MS,
            # PostgreSQL gives the times back with a time zone
            simulation_start_date=datetime(year=2025, month=1, day=1, tzinfo=timezone.utc),
            clients=[client_data.to_client_simulator_config()],
            database_config=database_config,
        ),
    )

    server.start_in_thread()
    server.wait_until_listening()
    SimpleTestClient.sending_accumulated_step_sizes(
        communication_protocol=communication_protocol,
        server_host="localhost",
        server_port=server_port,
        test_client_data=client_data,
        interface_name=OUTPUT_INTERFACE,
    ).start()
    server.assert_finishing_in_time()
    table = server.read_results()

    assert table.times == tuple(server.step_to_date(step) for step in range(STEPS))
    # PostgreSQL stores the names in lower case
    assert table.values(f"{client_data.simulator_name}.{OUTPUT_INTERFACE}") == [(step + 1) * STEP_SIZE_IN_MS / 1000 for step in range(STEPS)]
    assert table.state is SimulationState.FINISHED
