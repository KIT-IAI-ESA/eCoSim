from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.socket.esp_socket import ESPSocket, create_internal_socket
from ecosim_common.tech.parallel.parallel_lock import ParallelLock

_test_esp_socket: ESPSocket | None = None
_create_lock: ParallelLock = ParallelLock.thread()


# TODO_OSR: common abstraction between ESPSocket and ESPDask
def get_test_esp_socket() -> ESPSocket:
    global _test_esp_socket
    if _test_esp_socket is not None:
        return _test_esp_socket
    with _create_lock:
        if _test_esp_socket is None:
            _test_esp_socket = ESPSocket(create_internal_socket())
            _test_esp_socket.connect(ConnectionAddress("localhost", 33471))
        # noinspection PyTypeChecker
        return _test_esp_socket
