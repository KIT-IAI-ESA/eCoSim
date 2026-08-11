from typing import assert_never

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from integration_tests.test_data.generate_esp_dask import generate_dask_channel
from test_data.generate_esp_socket import generate_tcp_socket


def generate_esp_channel(
    communication_protocol: CommunicationProtocol,
) -> ESPChannel:
    match communication_protocol:
        case CommunicationProtocol.TCP_SOCKET:
            return generate_tcp_socket()
        case CommunicationProtocol.DASK:
            return generate_dask_channel()
        case _:
            assert_never(communication_protocol)
