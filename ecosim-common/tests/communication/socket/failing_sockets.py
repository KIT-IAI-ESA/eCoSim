import errno
import socket
import threading
from typing import Any, override


class SocketWhoseShutdownDoesNotWakeAccept(socket.socket):
    """Only Linux wakes accept() on shutdown(), so with this socket a close() relying on that fails on Linux too."""

    def __init__(self) -> None:
        super().__init__(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.accept_entered = threading.Event()

    @override
    def accept(self) -> tuple[socket.socket, Any]:
        self.accept_entered.set()
        return super().accept()

    @override
    def shutdown(self, how: int) -> None:
        raise OSError(errno.ENOTCONN, "not connected")
