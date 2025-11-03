import socket
import dask.distributed as dd
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

    @staticmethod
    def of_raw_dask_client_address(raw_address: str) -> "ConnectionAddress":
        split_address = raw_address.split(":")[1:]
        return ConnectionAddress(split_address[0][2:], int(split_address[1]))

    @staticmethod
    def of_dask_client(raw_dask_client: dd.Client) -> "ConnectionAddress":
        return ConnectionAddress.of_raw_dask_client_address(raw_dask_client.scheduler.addr)

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"
