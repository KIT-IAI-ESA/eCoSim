from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LogLine:
    level: str
    logger: str
    message: str

    @staticmethod
    def of_text(text: str) -> LogLine | None:
        # a line of ecosim_common.tech.logger.logger.default_log_format
        log_line_pattern = r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} - (?P<level>[A-Z]+) - (?P<logger>[^:]+): (?P<message>.*)"
        match = re.fullmatch(pattern=log_line_pattern, string=text.rstrip("\r\n"))
        return None if match is None else LogLine(level=match["level"], logger=match["logger"], message=match["message"])

    def is_a_warning_or_worse(self) -> bool:
        return self.level in ("WARNING", "ERROR", "CRITICAL")

    def is_an_error(self) -> bool:
        return self.level in ("ERROR", "CRITICAL")
