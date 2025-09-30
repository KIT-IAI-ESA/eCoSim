import socket
from dataclasses import dataclass
from typing import Tuple

type ConnectionAddressRaw = Tuple[str, int]


@dataclass(frozen=True)
class ConnectionAddress:
    ip: str
    port: int

    @staticmethod
    def of_raw_socket_address(raw_address: ConnectionAddressRaw) -> "ConnectionAddress":
        return ConnectionAddress(raw_address[0], raw_address[1])

    @staticmethod
    def of_socket(raw_socket: socket.socket) -> "ConnectionAddress":
        return ConnectionAddress.of_raw_socket_address(raw_socket.getsockname())

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"
