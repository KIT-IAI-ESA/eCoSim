import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_test_common.bounded_wait import finishes_in_time
from integration_tests.test_data.server_client.lost_client_setup import (
    HEALTHY,
    HOST,
    LOST,
    RUN_TIMEOUT_IN_SECONDS,
    SHORT_RESPONSE_TIMEOUTS,
    STEPS,
    crash_in_step,
)
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer


def test_failed_run_ends_the_healthy_client_as_failed_and_sets_the_state_to_failed(
    communication_protocol: CommunicationProtocol,
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = get_free_port()
    server = SimpleTestServer.for_client_ids(
        communication_protocol=communication_protocol,
        host=HOST,
        port=port,
        client_ids=(HEALTHY, LOST),
        steps=STEPS,
        response_timeouts=SHORT_RESPONSE_TIMEOUTS,
    )
    server_run = server.start_in_thread()
    server.wait_until_listening()
    healthy_client = SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=HEALTHY,
    )
    healthy_client.start()
    SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=LOST,
        on_simulation_step_return=crash_in_step,
    ).start()

    server_run.assert_ends_within(timeout_in_seconds=RUN_TIMEOUT_IN_SECONDS)

    assert finishes_in_time(blocking_call=healthy_client.wait_until_finished)
    assert healthy_client.exit_code() == ShutdownManager.FAILED_RUN_EXIT_CODE
    # the run failed because of the other client, so this one does not blame its own model
    assert any(message.startswith(f"{HEALTHY}: the connection to the server ended") for message in caplog.messages)
    assert server.simulation_state_repository().current() == SimulationState.FAILED
