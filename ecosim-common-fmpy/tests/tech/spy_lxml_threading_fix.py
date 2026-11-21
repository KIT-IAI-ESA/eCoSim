from dataclasses import dataclass, field
from time import sleep
from typing import override

from ecosim_common_fmpy.tech.fix_lxml_threading_issues import LxmlThreadingFix


@dataclass
class SpyLxmlThreadingFix(LxmlThreadingFix):
    delay_in_seconds: float = field(default=0.0)
    apply_count: int = field(default=0)

    @override
    def _apply(self) -> None:
        sleep(self.delay_in_seconds)
        self.apply_count += 1
        super()._apply()
