from typing import Any, Generator, cast

import pytest
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_test_common.test_data.generate_esp_channel import generate_esp_channel


@pytest.fixture(
    scope="function",
    params=[CommunicationProtocol.TCP_SOCKET, CommunicationProtocol.DASK],
)
def esp_channel(request: pytest.FixtureRequest) -> Generator[ESPChannel, Any, None]:
    communication_protocol: CommunicationProtocol = cast(CommunicationProtocol, request.param)
    channel = generate_esp_channel(communication_protocol)
    yield channel
    channel.close()
