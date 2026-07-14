from enum import Enum


class CommunicationProtocol(str, Enum):
    DASK = "dask"
    TCP_SOCKET = "tcp_socket"

    @staticmethod
    def of(protocol: str) -> "CommunicationProtocol":
        if protocol.lower() == "dask":
            return CommunicationProtocol.DASK
        if protocol.lower() == "tcp_socket" or protocol.lower() == "tcp-socket":
            return CommunicationProtocol.TCP_SOCKET
        raise ValueError(f"Type {protocol} not known")
