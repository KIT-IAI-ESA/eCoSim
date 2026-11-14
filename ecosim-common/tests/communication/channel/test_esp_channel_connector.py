import socket

import pytest

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_test_common.test_data.generate_connection_address import generate_unused_connection_address


def test_failed_tcp_connection_names_the_transport_and_the_address(caplog: pytest.LogCaptureFixture) -> None:
    address = generate_unused_connection_address()
    connector = ESPChannelConnector(_communication_protocol=CommunicationProtocol.TCP_SOCKET)

    with pytest.raises(ConnectionError) as error:
        connector.connect(connection_address=address, timeout_in_seconds=1)

    first_failure = next(record.getMessage() for record in caplog.records if record.name == "ESPChannelConnector" and record.levelname == "INFO")
    for message in (str(error.value), first_failure):
        assert "tcp_socket" in message
        assert str(address) in message
        assert "dask" not in message.lower()


def test_a_client_without_a_server_is_told_to_start_it_or_to_check_the_address() -> None:
    address = generate_unused_connection_address()
    connector = ESPChannelConnector(_communication_protocol=CommunicationProtocol.TCP_SOCKET)

    with pytest.raises(ConnectionError) as error:
        connector.connect(connection_address=address, timeout_in_seconds=1)

    assert str(error.value) == (
        f"No server answered at {address} via tcp_socket within 1 s. Start the server first, or check ip and port in the [server] section "
        + "of the client config, or --server-host and --server-port if you passed them."
    )


def test_a_server_that_does_not_listen_yet_is_reported_once_and_not_for_every_attempt(caplog: pytest.LogCaptureFixture) -> None:
    connector = ESPChannelConnector(_communication_protocol=CommunicationProtocol.TCP_SOCKET)

    with pytest.raises(ConnectionError):
        # a connect without a server takes 2 s on Windows
        connector.connect(connection_address=generate_unused_connection_address(), timeout_in_seconds=4)

    records = [record for record in caplog.records if record.name == "ESPChannelConnector"]
    assert len([record for record in records if record.levelname == "DEBUG"]) >= 2, "the connector tried only once"
    assert [record.levelname for record in records if record.levelname != "DEBUG"] == ["INFO"]


def test_successful_tcp_connection_names_the_transport_and_the_address(caplog: pytest.LogCaptureFixture) -> None:
    with socket.create_server(("127.0.0.1", 0)) as server:
        ip, port = server.getsockname()
        address = ConnectionAddress(ip=ip, port=port)

        ESPChannelConnector(_communication_protocol=CommunicationProtocol.TCP_SOCKET).connect(connection_address=address)

    assert f"Connected to the server at {address} via tcp_socket" in caplog.text
