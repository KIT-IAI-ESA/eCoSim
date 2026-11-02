import socket

from ecosim_common.communication.channel.connection_address import ConnectionAddress


def generate_unused_connection_address() -> ConnectionAddress:
    with socket.create_server(("127.0.0.1", 0)) as server:
        ip, port = server.getsockname()
    return ConnectionAddress(ip=ip, port=port)
