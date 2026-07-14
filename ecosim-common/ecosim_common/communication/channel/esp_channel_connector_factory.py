from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.dask.dask_connector import DaskConnector
from ecosim_common.communication.socket.socket_connector import SocketConnector


class ESPChannelConnectorFactory:
    @staticmethod
    def of_client_config(client_config: ClientConfig) -> ESPChannelConnector:
        if client_config.communication_protocol() == CommunicationProtocol.TCP_SOCKET:
            return SocketConnector()
        elif client_config.communication_protocol() == CommunicationProtocol.DASK:
            return DaskConnector()
        else:
            raise NotImplementedError(f"Communication protocol {client_config.communication_protocol()} not implemented yet")
