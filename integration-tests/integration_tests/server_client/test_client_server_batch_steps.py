from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.test_data.server_client.pre_set_two_clients_fixture import create_pre_set_two_clients
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer


def test_client_server_batch_steps(communication_protocol: CommunicationProtocol) -> None:
    run_client_server_batch_steps(communication_protocol)


def test_client_server_batch_steps_with_empty_repository(communication_protocol: CommunicationProtocol) -> None:
    run_client_server_batch_steps_with_empty_repository(communication_protocol)


def test_client_server_batch_steps_different_completed_steps_step4_step5(communication_protocol: CommunicationProtocol) -> None:
    run_client_server_batch_steps_different_completed_steps_step4_step5(communication_protocol)


def test_client_server_batch_steps_different_completed_steps_step1_step5(communication_protocol: CommunicationProtocol) -> None:
    run_client_server_batch_steps_different_completed_steps_step1_step5(communication_protocol)


def run_client_server_batch_steps(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    return _run_with_completed_steps(communication_protocol, client_1_completed_steps=5, client_2_completed_steps=5)


def run_client_server_batch_steps_with_empty_repository(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    return _run_with_completed_steps(communication_protocol, client_1_completed_steps=0, client_2_completed_steps=0)


def run_client_server_batch_steps_different_completed_steps_step4_step5(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    return _run_with_completed_steps(communication_protocol, client_1_completed_steps=4, client_2_completed_steps=5)


def run_client_server_batch_steps_different_completed_steps_step1_step5(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    return _run_with_completed_steps(communication_protocol, client_1_completed_steps=1, client_2_completed_steps=5)


def _run_with_completed_steps(
    communication_protocol: CommunicationProtocol,
    client_1_completed_steps: int,
    client_2_completed_steps: int,
) -> SimpleTestServer:
    """Stores the measurements of the already completed steps before the run, so the server continues from there."""
    pre_set_two_clients = create_pre_set_two_clients(communication_protocol)
    for step in range(client_1_completed_steps):
        pre_set_two_clients.add_client_1_measurement(
            step=step,
            output_value=pre_set_two_clients.client_1_output_value_at_step(step),
            input_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )
    for step in range(client_2_completed_steps):
        pre_set_two_clients.add_client_2_measurement(step=step, output_value=pre_set_two_clients.client_2_output_value_at_step(step))
    pre_set_two_clients.server.start_in_thread()
    pre_set_two_clients.server.wait_until_listening()
    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()
    pre_set_two_clients.server.assert_finishing_in_time()
    pre_set_two_clients.server.print_measurement_statistics()
    pre_set_two_clients.verify_successful_run()
    return pre_set_two_clients.server
