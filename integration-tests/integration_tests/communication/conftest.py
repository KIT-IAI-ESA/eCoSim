from typing import Generator, Any, cast, assert_never

import pytest

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.socket.socket_channel import SocketChannel
from integration_tests.test_data.generate_esp_dask import generate_esp_dask
from integration_tests.test_data.generate_esp_socket import generate_esp_socket


@pytest.fixture(
    scope="function",
    params=[CommunicationProtocol.TCP_SOCKET, CommunicationProtocol.DASK],
)
def esp_channel(request: pytest.FixtureRequest) -> Generator[ESPChannel, Any, None]:
    communication_protocol: CommunicationProtocol = cast(CommunicationProtocol, request.param)
    channel: ESPChannel
    match communication_protocol:
        case CommunicationProtocol.TCP_SOCKET:
            channel = SocketChannel(_internal_socket=generate_esp_socket())
        case CommunicationProtocol.DASK:
            channel = DaskChannel(_internal_dask_client=generate_esp_dask())
        case _:
            assert_never(communication_protocol)

    yield channel

    channel.close()
