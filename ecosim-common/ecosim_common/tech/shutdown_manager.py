from __future__ import annotations

import faulthandler
import signal
import sys
import threading
import time
import traceback
from abc import ABC, abstractmethod
from types import FrameType
from typing import Any, Dict, Type

import dask.distributed as dd
from ecosim_common.tech.logger.logger import ESPLogger

# signals this soon after a shutdown started or another signal are ignored: 'uv run' delivers one kill of the process group twice
SIGNAL_GRACE_IN_SECONDS = 3


class ShutdownListener(ABC):
    @abstractmethod
    def on_app_shutdown(self) -> None:
        pass


class ShutdownManager:
    SUCCESS_EXIT_CODE: int = 0
    # the same code Python exits with on an uncaught exception
    FAILED_RUN_EXIT_CODE: int = 1
    INTERRUPT_EXIT_CODE: int = 33
    TERMINATE_EXIT_CODE: int = 44
    _instance = None
    _lock = threading.Lock()
    _logger = ESPLogger("ShutdownManager")
    _listener: Dict[int, ShutdownListener] = {}
    _signal_handlers_installed: bool = False
    _ignore_signals_until: float = 0.0
    shutdown_event: threading.Event | dd.Event

    def __new__(
        cls: Type[ShutdownManager],
        *args: Any,
        **kwargs: Any,
    ) -> ShutdownManager:
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    instance = super(ShutdownManager, cls).__new__(cls, *args, **kwargs)
                    try:  # If dask client present, use dask.distributed.Event
                        dd.get_client()
                        instance.shutdown_event = dd.Event()
                    except ValueError:  # otherwise normal threading.Event
                        instance.shutdown_event = threading.Event()
                    cls._instance = instance
        return cls._instance

    def __reduce__(self) -> tuple[Type[ShutdownManager], tuple[()]]:
        """
        Sends the recipe for the singleton instead of a copy of this one.

        A copy would carry this process' resources - among them a non-picklable 'threading.Event' - and
        shutting it down would leave the receiving process, which is the one that has to release something,
        untouched.
        """
        return (ShutdownManager, ())

    def init(self, install_signal_handlers: bool = True) -> None:
        if install_signal_handlers:
            self.__install_signal_handlers_once()
        if not faulthandler.is_enabled():
            faulthandler.enable()

    def __install_signal_handlers_once(self) -> None:
        if ShutdownManager._signal_handlers_installed:
            return
        signal.signal(signal.SIGINT, self.__interrupt_signal_handler)
        signal.signal(signal.SIGTERM, self.__terminate_signal_handler)
        ShutdownManager._signal_handlers_installed = True

    # noinspection PyUnusedLocal
    def __interrupt_signal_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        self.__exit_on_signal(signal_name="Interrupt", exit_code=self.INTERRUPT_EXIT_CODE)

    # noinspection PyUnusedLocal
    def __terminate_signal_handler(
        self,
        sig: int,
        frame: FrameType | None,
    ) -> None:
        self.__exit_on_signal(signal_name="Terminate", exit_code=self.TERMINATE_EXIT_CODE)

    def __exit_on_signal(
        self,
        signal_name: str,
        exit_code: int,
    ) -> None:
        if time.monotonic() < ShutdownManager._ignore_signals_until:
            return
        self._logger.info("%s signal received - shutting down.", signal_name)
        self.__trigger_shutdown()
        sys.exit(exit_code)

    def __trigger_shutdown(self) -> None:
        ShutdownManager._ignore_signals_until = time.monotonic() + SIGNAL_GRACE_IN_SECONDS
        if self.shutdown_event.is_set():
            self._logger.debug("Shutdown was already triggered - listeners stay untouched.")
            return
        self.shutdown_event.set()
        for listener in list(self._listener.values()):
            self.__pop_and_notify(listener)
        self._logger.debug("All listeners notified.")

    def __pop_and_notify(
        self,
        listener: ShutdownListener,
    ) -> None:
        if self._listener.pop(id(listener), None) is None:
            return
        # a further signal raises SystemExit inside the running listener: catching it skips a hanging listener, the next ones still run
        try:
            listener.on_app_shutdown()
        except (Exception, SystemExit):
            self._logger.error("Shutdown listener %s failed:\n%s", type(listener).__name__, traceback.format_exc())

    def register_listener(
        self,
        listener: ShutdownListener,
    ) -> None:
        # add before checking, so a shutdown starting right now cannot miss it
        self._listener[id(listener)] = listener
        if self.shutdown_event.is_set():
            self._logger.warning("Shutdown event already set - notifying listener.")
            self.__pop_and_notify(listener)

    def is_shutdown(self) -> bool:
        return self.shutdown_event.is_set()

    def set_shutdown_at_application_end(self) -> None:
        self._logger.debug("Shutdown was triggered at the end of the application.")
        self.__trigger_shutdown()

    @staticmethod
    def reset_instance() -> None:
        ShutdownManager._listener.clear()
        ShutdownManager._signal_handlers_installed = False
        ShutdownManager._instance = None
        ShutdownManager._ignore_signals_until = 0.0
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
