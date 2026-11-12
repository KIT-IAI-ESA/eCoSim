from pathlib import Path
from typing import Any

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from integration_tests.test_data.server_client.logical_delay_setup import (
    RecordingReceiver,
    delayed_simulation_config,
    receiver_client,
    sender_client,
    server_on_free_port,
)


def _sent_matrix(seconds: float) -> Any:
    return [[seconds, seconds + 0.25], [seconds + 0.5, seconds + 0.75]]


def test_list_start_value_arrives_until_the_first_delayed_list(communication_protocol: CommunicationProtocol, tmp_path: Path) -> None:
    simulation_config = delayed_simulation_config(directory=tmp_path, steps=4, delay=2, start_value=[[-1.0, -2.0], [-3.0, -4.0]])
    server = server_on_free_port(communication_protocol=communication_protocol, simulation_config=simulation_config)
    receiver = RecordingReceiver()

    server.start_in_thread()
    server.wait_until_listening()
    sender_client(server=server, sent_value_after_seconds=_sent_matrix).start()
    receiver_client(server=server, receiver=receiver, interface="delayed").start()
    server.assert_finishing_in_time()

    assert receiver.received_inputs["delayed"] == [
        [[-1.0, -2.0], [-3.0, -4.0]],
        [[-1.0, -2.0], [-3.0, -4.0]],
        [[1.0, 1.25], [1.5, 1.75]],
        [[2.0, 2.25], [2.5, 2.75]],
    ]
