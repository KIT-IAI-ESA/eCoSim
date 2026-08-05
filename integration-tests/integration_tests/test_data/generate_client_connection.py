from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.client_connection import ClientConnection
from integration_tests.test_data.generate_esp_channel import generate_esp_channel


def generate_client_connection(
    communication_protocol: CommunicationProtocol,
) -> ClientConnection:
    return ClientConnection(
        address=ConnectionAddress("localhost", 8080),
        _channel=generate_esp_channel(communication_protocol),
    )
