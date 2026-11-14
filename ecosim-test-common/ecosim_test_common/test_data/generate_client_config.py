from unittest.mock import MagicMock

from ecosim_common.client.config.client_config import ClientConfig, ServerConfig
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID


def generate_mocked_client_config(
    communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    server_address: ConnectionAddress | None = None,
    client_id: ClientID | None = None,
) -> ClientConfig:
    """Answers only the communication protocol, and the server address and the client id if they are given."""
    client_config = MagicMock(spec=ClientConfig)
    client_config.communication_protocol.return_value = communication_protocol
    if server_address is not None:
        client_config.server_config.return_value = ServerConfig(server_address=server_address, communication_protocol=communication_protocol)
    if client_id is not None:
        client_config.client_id.return_value = client_id
    return client_config
