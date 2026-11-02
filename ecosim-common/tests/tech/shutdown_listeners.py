import signal
from dataclasses import dataclass, field
from typing import override

from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass
class CountingShutdownListener(ShutdownListener):
    notification_count: int = field(default=0)

    @override
    def on_app_shutdown(self) -> None:
        self.notification_count += 1


@dataclass
class OrderRecordingShutdownListener(ShutdownListener):
    name: str
    notified_names: list[str]

    @override
    def on_app_shutdown(self) -> None:
        self.notified_names.append(self.name)


@dataclass
class RaisingShutdownListener(ShutdownListener):
    notified: bool = field(default=False)

    @override
    def on_app_shutdown(self) -> None:
        self.notified = True
        raise RuntimeError("listener failed")


@dataclass
class SignalRaisingShutdownListener(ShutdownListener):
    finished: bool = field(default=False)

    @override
    def on_app_shutdown(self) -> None:
        signal.raise_signal(signal.SIGTERM)
        self.finished = True


@dataclass
class GraceEndingSignalRaisingShutdownListener(ShutdownListener):
    finished: bool = field(default=False)

    @override
    def on_app_shutdown(self) -> None:
        ShutdownManager._ignore_signals_until = 0.0  # noqa: SLF001
        signal.raise_signal(signal.SIGTERM)
        self.finished = True
