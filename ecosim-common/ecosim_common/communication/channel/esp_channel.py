from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Protocol

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass(kw_only=True)
class ESPChannel(ABC):
    @staticmethod
    def for_protocol(
        communication_protocol: CommunicationProtocol,
        connection_address: ConnectionAddress,
        dask_id: str | None = None,
    ) -> ESPChannel:
        match communication_protocol:
            case CommunicationProtocol.DASK:
                from ecosim_common.communication.dask.dask_channel import DaskChannel

                return DaskChannel.of(
                    connection_address=connection_address,
                    dask_id=dask_id,
                )
            case CommunicationProtocol.TCP_SOCKET:
                from ecosim_common.communication.socket.tcp_socket import TCPSocket

                return TCPSocket.create(connection_address)
            case _:
                raise ValueError(f"Unknown communication protocol: {communication_protocol}")

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def listen_on_message_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        pass

    @abstractmethod
    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        """
        :return ESPChannelMessage | None: The received message or None if the connection was closed.
        """
        pass

    @abstractmethod
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        pass

    @abstractmethod
    def wait_for_finish(self) -> None:
        pass

    @abstractmethod
    def is_listening_event(self) -> ParallelEvent:
        pass

    @abstractmethod
    def listen_on_connection_loop_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        pass

    @abstractmethod
    def is_listening_on_connection_event(self) -> ParallelEvent:
        pass


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
