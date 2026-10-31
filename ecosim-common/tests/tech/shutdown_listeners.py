from dataclasses import dataclass, field
from typing import override

from ecosim_common.tech.shutdown_manager import ShutdownListener


@dataclass
class CountingShutdownListener(ShutdownListener):
    notification_count: int = field(default=0)

    @override
    def on_app_shutdown(self) -> None:
        self.notification_count += 1


class RaisingShutdownListener(ShutdownListener):
    @override
    def on_app_shutdown(self) -> None:
        raise RuntimeError("listener failed")
