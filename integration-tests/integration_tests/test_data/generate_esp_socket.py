from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.socket.tcp_socket import TCPSocket


# TODO_OSR: common abstraction between ESPSocket and ESPDask
def generate_tcp_socket() -> TCPSocket:
    _test_esp_socket = TCPSocket.create(
        connection_address=ConnectionAddress("localhost", 33471),
    )
    _test_esp_socket.connect()
    return _test_esp_socket
