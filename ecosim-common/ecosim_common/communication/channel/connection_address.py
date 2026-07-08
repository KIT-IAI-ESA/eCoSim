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
        connection_type, address = dd.comm.parse_address(raw_address)
        if connection_type == "tcp":
            split_address = address.split(":")
            return ConnectionAddress(split_address[0], int(split_address[1]))
        else:
            assert connection_type == "inproc"
            split_address = address.split("/")
            return ConnectionAddress(split_address[0], split_address[1]+"/"+split_address[2])

    @staticmethod
    def of_dask_client(raw_dask_client: dd.Client) -> "ConnectionAddress":
        if not raw_dask_client.scheduler:
            raise AttributeError
        else:
            return ConnectionAddress.of_raw_dask_client_address(raw_dask_client.scheduler.addr)

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"
