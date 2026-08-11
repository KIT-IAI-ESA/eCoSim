from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol


# TODO_OSR: implement stop listening function
@dataclass(frozen=True)
class ESPChannelEndpoint(ABC):
    # TODO_OSR: think about returning an ESPQueue
    @abstractmethod
    def listen_on_connection_loop_async(
        self,
        channel_handler: ChannelHandler,
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

                return EndpointSocket.for_connection_address(connection_address)
            case _:
                raise ValueError(f"Unknown communication protocol: {communication_protocol}")


@dataclass(frozen=True)
class ConnectionData:
    channel: ESPChannel
    client_address: ConnectionAddress


class ChannelHandler(Protocol):
    """Invoked once per accepted channel, in a dedicated execution context
    owned by the endpoint (thread, seceded dask task, ...).

    MAY block for the entire lifetime of the channel. Endpoint implementations
    must not assume it returns promptly.
    """

    def __call__(
        self,
        connection_data: ConnectionData,
    ) -> None: ...
