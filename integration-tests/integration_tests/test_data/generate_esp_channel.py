from typing import assert_never

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.socket.socket_channel import SocketChannel
from integration_tests.test_data.generate_esp_dask import get_test_esp_dask
from integration_tests.test_data.generate_esp_socket import get_test_esp_socket


def generate_esp_channel(communication_protocol: CommunicationProtocol) -> ESPChannel:
    match communication_protocol:
        case CommunicationProtocol.TCP_SOCKET:
            return SocketChannel(get_test_esp_socket())
        case CommunicationProtocol.DASK:
            return DaskChannel(get_test_esp_dask())
        case _:
            assert_never(communication_protocol)
