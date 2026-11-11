import errno
import socket

import pytest

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.tech.port_utils import get_free_port
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServerParameters, generate_simple_test_server

LOOPBACK_IP = "127.0.0.1"


def test_server_start_raises_on_a_busy_port() -> None:
    with socket.create_server((LOOPBACK_IP, 0)) as occupant:
        server = generate_simple_test_server(
            SimpleTestServerParameters(
                communication_protocol=CommunicationProtocol.TCP_SOCKET,
                host=LOOPBACK_IP,
                port=occupant.getsockname()[1],
            ),
        )

        with pytest.raises(OSError) as error:
            server.start()

    assert error.value.errno == errno.EADDRINUSE


def test_server_bound_to_the_loopback_ip_runs_a_local_client() -> None:
    port = get_free_port()
    steps = 3
    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=CommunicationProtocol.TCP_SOCKET,
            host=LOOPBACK_IP,
            port=port,
            steps=steps,
        ),
    )
    client = SimpleTestClient.generate(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        server_host=LOOPBACK_IP,
        server_port=port,
        on_simulation_step_return=lambda *_: ClientSimStepData(interface_values=[]),
    )

    server.start_in_thread()
    server.wait_until_listening()
    client.start()

    server.assert_finishing_in_time()
    client_measurement_repository = server.measurement_repository(client_id=client.client_id)
    assert isinstance(client_measurement_repository, MeasurementRepositoryInMemory)
    client_measurement_repository.assert_entry_count(steps)
