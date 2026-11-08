from __future__ import annotations

import socket
from dataclasses import dataclass

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from ecosim_test_common.bounded_listen import listen_blocking_bounded
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS


@dataclass
class SingleConnectionServer:
    """Serves one client with the messages a test chooses, then hangs up."""

    _listening_socket: socket.socket

    @staticmethod
    def listen() -> SingleConnectionServer:
        listening_socket = socket.create_server(("127.0.0.1", 0))
        listening_socket.settimeout(WAIT_TIMEOUT_IN_SECONDS)
        return SingleConnectionServer(_listening_socket=listening_socket)

    def address(self) -> ConnectionAddress:
        return ConnectionAddress.of_raw_socket_address(self._listening_socket.getsockname())

    def serve(self, message_types: list[MessageType]) -> None:
        channel = self._accept()
        for message_type in message_types:
            channel.send(ESPChannelMessageJson.empty(type=message_type))
            # no answer: the client closed the connection
            if listen_blocking_bounded(channel=channel) is None:
                break
        channel.close()

    def _accept(self) -> TCPSocket:
        with self._listening_socket:
            connection, client_address = self._listening_socket.accept()
        return TCPSocket(_internal_socket=connection, _connection_address=ConnectionAddress.of_raw_socket_address(client_address))
