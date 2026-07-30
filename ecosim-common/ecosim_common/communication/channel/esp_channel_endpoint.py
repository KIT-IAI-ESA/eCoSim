from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol


# TODO_OSR: implement stop listening function
@dataclass(frozen=True)
class ESPChannelEndpoint(ABC):
    # TODO_OSR: think about returning an ESPQueue
    @abstractmethod
    def listen_async(
        self,
        on_new_channel: Callable[[ConnectionData], None],
    ) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @staticmethod
    def for_protocol(
        communication_protocol: CommunicationProtocol,
        connection_address: ConnectionAddress,
    ) -> ESPChannelEndpoint:
        match communication_protocol:
            case CommunicationProtocol.DASK:
                from ecosim_common.communication.dask.endpoint_dask import EndpointDask

                return EndpointDask(connection_address)
            case CommunicationProtocol.TCP_SOCKET:
                from ecosim_common.communication.socket.endpoint_socket import EndpointSocket

                return EndpointSocket(connection_address)
            case _:
                raise ValueError(f"Unknown communication protocol: {communication_protocol}")


@dataclass(frozen=True)
class ConnectionData:
    channel: ESPChannel
    client_address: ConnectionAddress
