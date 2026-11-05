from typing import Callable

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client import test_client_server_batch_steps as batch_steps
from integration_tests.server_client.performance.tooling.assert_performance import assert_performance
from integration_tests.server_client.test_codependent_clients_server import run_codependent_clients_server
from integration_tests.server_client.test_matrix_transfer import run_matrix_transfer
from integration_tests.server_client.test_single_client_server import run_client_server_single
from integration_tests.server_client.test_three_client_server import run_three_clients_server
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer

RunTest = Callable[[CommunicationProtocol], SimpleTestServer]


@pytest.mark.parametrize(
    ("test_name", "run"),
    [
        ("test_client_server_single", run_client_server_single),
        ("test_three_clients_server", run_three_clients_server),
        ("test_codependent_clients_server", run_codependent_clients_server),
        ("test_matrix_transfer", run_matrix_transfer),
        ("test_client_server_batch_steps", batch_steps.run_client_server_batch_steps),
        ("test_client_server_batch_steps_with_empty_repository", batch_steps.run_client_server_batch_steps_with_empty_repository),
        (
            "test_client_server_batch_steps_different_completed_steps_step4_step5",
            batch_steps.run_client_server_batch_steps_different_completed_steps_step4_step5,
        ),
        (
            "test_client_server_batch_steps_different_completed_steps_step1_step5",
            batch_steps.run_client_server_batch_steps_different_completed_steps_step1_step5,
        ),
    ],
    ids=lambda value: value.removeprefix("test_") if isinstance(value, str) else "",
)
def test_client_server_performance(test_name: str, run: RunTest, communication_protocol: CommunicationProtocol) -> None:
    """Each `run` executes the integration test and returns its server; `test_name` is the name the results are stored under."""
    assert_performance(
        test_name=test_name,
        run_test=lambda: run(communication_protocol).server_measurements,
        communication_protocol=communication_protocol,
    )
