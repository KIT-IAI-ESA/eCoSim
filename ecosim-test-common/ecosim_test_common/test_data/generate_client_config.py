from unittest.mock import MagicMock

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol


def generate_mocked_client_config(
    communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
) -> ClientConfig:
    """A config that only answers what every 'Client' needs on creation: its communication protocol."""
    client_config = MagicMock(spec=ClientConfig)
    client_config.communication_protocol.return_value = communication_protocol
    return client_config
