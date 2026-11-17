from unittest.mock import MagicMock

from ecosim_common.client.config.client_config import ClientConfig, ClientInterfaceConfig, ServerConfig, SimulatorConfig
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.config.client_id import ClientID
from ecosim_test_common.resources.resource_utils import fmc_path


def generate_mocked_client_config(
    communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    server_address: ConnectionAddress | None = None,
    client_id: ClientID | None = None,
    simulator_config: SimulatorConfig | None = None,
) -> ClientConfig:
    """Answers the communication protocol and only the other values that are given."""
    client_config = MagicMock(spec=ClientConfig)
    client_config.communication_protocol.return_value = communication_protocol
    if server_address is not None:
        client_config.server_config.return_value = ServerConfig(server_address=server_address, communication_protocol=communication_protocol)
    if client_id is not None:
        client_config.client_id.return_value = client_id
        client_config.meta_data.return_value = ClientMetaData(version="2.0", simulator_name=client_id.simulator_name, model_name=client_id.model_name)
    if simulator_config is not None:
        client_config.simulator_config.return_value = simulator_config
        interfaces_config = ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=fmc_path())
        client_config.interfaces_config.return_value = interfaces_config
    return client_config
