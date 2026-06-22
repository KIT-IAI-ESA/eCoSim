from __future__ import annotations

import signal
import sys
import threading
import dask.distributed as dd
from abc import ABC, abstractmethod
from types import FrameType
from typing import List, Type, Any

from ecosim_common.tech.logger.logger import ESPLogger


class ShutdownListener(ABC):
    @abstractmethod
    def on_app_shutdown(self) -> None:
        """This method must be implemented by the subclass."""
        pass


class ShutdownManager:
    _instance = None
    _lock = threading.Lock()
    _logger = ESPLogger("ShutdownManager")
    _listener: List[ShutdownListener] = []
    _init: bool = False
    shutdown_event: threading.Event | dd.Event

    def __new__(
        cls: Type[ShutdownManager],
        *args: Any,
        **kwargs: Any,
    ) -> ShutdownManager:
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ShutdownManager, cls).__new__(cls, *args, **kwargs)
                    try:  # If dask client present, use dask.distributed.Event
                        dd.get_client()
                        cls._instance.shutdown_event = dd.Event()
                    except ValueError:  # otherwise normal threading.Event
                        cls._instance.shutdown_event = threading.Event()
        return cls._instance

    def init(self) -> None:
        if ShutdownManager._init:
            return
        signal.signal(signal.SIGINT, self.__interrupt_signal_handler)
        signal.signal(signal.SIGTERM, self.__terminate_signal_handler)
        # Setup handlers for exception-related signals
        signal.signal(signal.SIGSEGV, self.__other_interrupts_handler)
        signal.signal(signal.SIGABRT, self.__other_interrupts_handler)
        signal.signal(signal.SIGFPE, self.__other_interrupts_handler)

    # noinspection PyUnusedLocal
    def __interrupt_signal_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        if self.shutdown_event.is_set():
            return
        self._logger.info("Interrupt signal received - shutting down.")
        self.__trigger_shutdown()
        sys.exit(333)

    # noinspection PyUnusedLocal
    def __terminate_signal_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        if self.shutdown_event.is_set():
            return
        self._logger.info("Terminate signal received - shutting down.")
        self.__trigger_shutdown()
        sys.exit(444)

    # noinspection PyUnusedLocal
    def __other_interrupts_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        if self.shutdown_event.is_set():
            return
        self._logger.info("Other interrupt signal received - shutting down.")
        self.__trigger_shutdown()
        sys.exit(555)

    def __trigger_shutdown(self) -> None:
        self.shutdown_event.set()
        with (self._lock):
            for listener in self._listener:
                if listener is not None:
                    listener.on_app_shutdown()
            self._logger.debug("All listeners notified - resetting ShutdownManager itself.")
            self._listener.clear()
            self._instance = None
            self._shutdown_event = None
            self._init = False

    def register_listener(
        self,
        listener: ShutdownListener,
    ) -> None:
        with self._lock:
            self._listener.append(listener)

    def is_shutdown(self) -> bool:
        return self.shutdown_event.is_set()

    def set_shutdown_at_application_end(self) -> None:
        self._logger.debug("Shutdown was triggered at the end of the application.")
        self.__trigger_shutdown()

    def set_dask_shutdown(self) -> None:
        self._logger.debug("Shutting down simulators on Dask Client")
        self.__trigger_shutdown()


class ShutdownCommDask:
    def init(self) -> None:
        signal.signal(signal.SIGINT, self._interrupt_signal_handler)
        signal.signal(signal.SIGTERM, self._terminate_signal_handler)
        # Setup handlers for exception-related signals
        signal.signal(signal.SIGSEGV, self._other_interrupts_handler)
        signal.signal(signal.SIGABRT, self._other_interrupts_handler)
        signal.signal(signal.SIGFPE, self._other_interrupts_handler)
        self._dask_client = dd.get_client()

    def _interrupt_signal_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        print("PROCESS INTERRUPTED!!!!!!!")
        self._dask_client.run(ShutdownManager().set_dask_shutdown, wait=True)
        self._dask_client.shutdown()
        self._dask_client.close()

    def _terminate_signal_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        self._dask_client.run(ShutdownManager().set_dask_shutdown, wait=True)
        self._dask_client.shutdown()
        self._dask_client.close()

    def _other_interrupts_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        self._dask_client.run(ShutdownManager.set_dask_shutdown, wait=True)
        self._dask_client.shutdown()
        self._dask_client.close()
