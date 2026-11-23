from dataclasses import dataclass
from pathlib import Path

from ecosim_server.progress_logger import progress_logger

from ecosim.run.log_line import LogLine


# a log file never blocks the server as a full pipe would
@dataclass
class ServerLogFollower:
    log_file: Path
    read_up_to: int

    def new_log_lines(self) -> list[LogLine]:
        return [log_line for text in self._new_complete_lines() if (log_line := LogLine.of_text(text=text)) is not None]

    def _new_complete_lines(self) -> list[str]:
        if not self.log_file.is_file():
            return []
        with self.log_file.open("rb") as log:
            log.seek(self.read_up_to)
            new_bytes = log.read()
        # a line the server is still writing is read at the next call
        complete_bytes = new_bytes[: new_bytes.rfind(b"\n") + 1]
        self.read_up_to += len(complete_bytes)
        return complete_bytes.decode(encoding="utf-8", errors="replace").splitlines()


def line_to_show(log_line: LogLine, shows_warnings: bool) -> str | None:
    if log_line.logger == progress_logger.name:
        return log_line.message
    return f"server: {log_line.message}" if shows_warnings and log_line.is_a_warning_or_worse() else None
