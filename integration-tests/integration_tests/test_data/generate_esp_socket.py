from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.socket.esp_socket import ESPSocket, create_internal_socket


# TODO_OSR: common abstraction between ESPSocket and ESPDask
def generate_esp_socket() -> ESPSocket:
    _test_esp_socket = ESPSocket(create_internal_socket())
    _test_esp_socket.connect(ConnectionAddress("localhost", 33471))
    return _test_esp_socket
