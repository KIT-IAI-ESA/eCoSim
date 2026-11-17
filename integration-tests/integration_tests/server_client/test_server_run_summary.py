from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
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


def test_the_summary_of_a_finished_run_counts_every_step(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server = SimpleTestServer.for_client_ids(communication_protocol=communication_protocol, host=HOST, port=port, client_ids=(HEALTHY,), steps=STEPS)
    server.start_in_thread()
    server.wait_until_listening()
    SimpleTestClient.of_client_id(communication_protocol=communication_protocol, server_host=HOST, server_port=port, client_id=HEALTHY).start()

    server.assert_finishing_in_time()

    summary = server.run_summary()
    assert (summary.header(), summary.completed_steps) == ("SIMULATION FINISHED", STEPS)


def test_the_summary_of_a_failed_run_gives_the_error_as_the_reason(communication_protocol: CommunicationProtocol) -> None:
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
    SimpleTestClient.of_client_id(communication_protocol=communication_protocol, server_host=HOST, server_port=port, client_id=HEALTHY).start()
    SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=LOST,
        on_simulation_step_return=crash_in_step,
    ).start()

    server_run.assert_ends_within(timeout_in_seconds=RUN_TIMEOUT_IN_SECONDS)

    summary = server.run_summary()
    assert summary.header() == "SIMULATION FAILED"
    assert summary.failure_reason == str(server_run.error)


def test_a_run_that_the_shutdown_of_a_signal_ends_counts_as_stopped_by_a_signal(communication_protocol: CommunicationProtocol) -> None:
    server = SimpleTestServer.for_client_ids(
        communication_protocol=communication_protocol,
        host=HOST,
        port=get_free_port(),
        client_ids=(HEALTHY,),
        steps=STEPS,
    )
    server_run = server.start_in_thread()
    server.wait_until_listening()

    ShutdownManager().set_shutdown_at_application_end()

    server_run.assert_ends_within(timeout_in_seconds=RUN_TIMEOUT_IN_SECONDS)
    assert server.run_summary().failure_reason == "stopped by Ctrl-C or a kill signal"
