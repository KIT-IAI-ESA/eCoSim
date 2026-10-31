import socket

import pytest

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.communication_protocol import CommunicationProtocol


def _address_nobody_listens_on() -> ConnectionAddress:
    with socket.create_server(("127.0.0.1", 0)) as server:
        ip, port = server.getsockname()
    return ConnectionAddress(ip=ip, port=port)


def test_failed_tcp_connection_names_the_transport_and_the_address(caplog: pytest.LogCaptureFixture) -> None:
    address = _address_nobody_listens_on()
    connector = ESPChannelConnector(_communication_protocol=CommunicationProtocol.TCP_SOCKET)

    with pytest.raises(ConnectionError) as error:
        connector.connect(connection_address=address, timeout_in_seconds=1)

    warning = next(record.getMessage() for record in caplog.records if record.levelname == "WARNING")
    for message in (str(error.value), warning):
        assert "tcp_socket" in message
        assert str(address) in message
        assert "dask" not in message.lower()


def test_successful_tcp_connection_names_the_transport_and_the_address(caplog: pytest.LogCaptureFixture) -> None:
    with socket.create_server(("127.0.0.1", 0)) as server:
        ip, port = server.getsockname()
        address = ConnectionAddress(ip=ip, port=port)

        ESPChannelConnector(_communication_protocol=CommunicationProtocol.TCP_SOCKET).connect(connection_address=address)

    assert f"Connected to {address} via tcp_socket" in caplog.text
