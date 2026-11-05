from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.run_performance_test import assert_performance
from integration_tests.test_data.server_client.pre_set_two_clients import PreSetTwoClientsData


def test_client_server_batch_steps_performance(
    pre_set_two_clients: PreSetTwoClientsData,
    communication_protocol: CommunicationProtocol,
) -> None:
    from integration_tests.server_client import test_client_server_batch_steps as batch_steps

    assert_performance(
        test=batch_steps.test_client_server_batch_steps,
        test_argument=pre_set_two_clients,
        server_measurement=pre_set_two_clients.server.server_measurements,
        communication_protocol=communication_protocol,
    )
