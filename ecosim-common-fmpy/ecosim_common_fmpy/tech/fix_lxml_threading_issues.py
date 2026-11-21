from dataclasses import dataclass, field
from threading import Lock


@dataclass
class LxmlThreadingFix:
    _lock: Lock = field(default_factory=Lock)
    _is_applied: bool = field(default=False)

    def apply_once(self) -> None:
        with self._lock:
            if self._is_applied:
                return
            self._apply()
            self._is_applied = True

    def _apply(self) -> None:
        # the following lines try to mitigate multi-threading issues resulting (indirectly) from the fmpy library
        # s. `docs/content/development/tech/multi-threading-fmpy.md` for details
        try:
            import ctypes

            from lxml import etree

            lib = ctypes.CDLL(etree.__file__)
            lib.xmlSchemaInitTypes()

        except Exception:
            pass


PROCESS_LXML_THREADING_FIX = LxmlThreadingFix()
