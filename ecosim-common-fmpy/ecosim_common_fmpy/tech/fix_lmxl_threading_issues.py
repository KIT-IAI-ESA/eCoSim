from dataclasses import dataclass, field
from threading import Lock
from typing import Callable


def fix_lmxl_threading_issues() -> None:
    # the following lines try to mitigate multi-threading issues resulting (indirectly) from the fmpy library
    # s. `docs/content/development/tech/multi-threading-fmpy.md` for details
    try:
        import ctypes

        from lxml import etree

        lib = ctypes.CDLL(etree.__file__)
        lib.xmlSchemaInitTypes()

    except Exception:
        pass


@dataclass
class LxmlThreadingFix:
    fix: Callable[[], None] = field(default=fix_lmxl_threading_issues)
    _lock: Lock = field(default_factory=Lock)
    _is_applied: bool = field(default=False)

    def apply_once(self) -> None:
        with self._lock:
            if self._is_applied:
                return
            self.fix()
            self._is_applied = True


PROCESS_LXML_THREADING_FIX = LxmlThreadingFix()
