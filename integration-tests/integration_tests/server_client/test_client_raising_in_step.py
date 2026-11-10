from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from integration_tests.test_data.server_client.lost_client_setup import (
    HEALTHY,
    HOST,
    LOST,
    RUN_TIMEOUT_IN_SECONDS,
    SHORT_RESPONSE_TIMEOUTS,
    STEPS,
    assert_naming_the_lost_client,
    raise_in_step,
)
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer


def test_client_raising_in_a_step_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
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
        on_simulation_step_return=raise_in_step,
    ).start()

    assert_naming_the_lost_client(server_run=server_run, timeout_in_seconds=RUN_TIMEOUT_IN_SECONDS, waiting_for="response of step")
