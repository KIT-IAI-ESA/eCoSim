from typing import Any, Generator, assert_never, cast

import pytest
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from integration_tests.test_data.generate_esp_dask import generate_dask_channel
from integration_tests.test_data.generate_esp_socket import generate_tcp_socket


@pytest.fixture(
    scope="function",
    params=[CommunicationProtocol.TCP_SOCKET, CommunicationProtocol.DASK],
)
def esp_channel(request: pytest.FixtureRequest) -> Generator[ESPChannel, Any, None]:
    communication_protocol: CommunicationProtocol = cast(CommunicationProtocol, request.param)
    channel: ESPChannel
    match communication_protocol:
        case CommunicationProtocol.TCP_SOCKET:
            channel = generate_tcp_socket()
        case CommunicationProtocol.DASK:
            channel = generate_dask_channel()
        case _:
            assert_never(communication_protocol)

    yield channel

    channel.close()
