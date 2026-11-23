import re
from pathlib import Path

from ecosim_common.tech.one_line_errors import DEBUG_HINT

from ecosim.run.log_line import LogLine

# the one line a console script ends an error with
ERROR_LINE = r"[\w-]+: error: .*"


def reason_lines(log_file: Path, start: int, count: int = 5) -> list[str]:
    """Returns the errors and the end of a traceback in the log, else its last lines."""
    with log_file.open("rb") as log:
        log.seek(start)
        text = log.read().decode(encoding="utf-8", errors="replace")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    reasons = _reasons_in(lines=lines)
    # an error is often logged and then printed again as the last line
    return list(dict.fromkeys(reasons or lines))[-count:]


def _reasons_in(lines: list[str]) -> list[str]:
    reasons: list[str] = []
    in_an_error_of_several_lines = False
    for line in lines:
        if in_an_error_of_several_lines:
            in_an_error_of_several_lines = line != DEBUG_HINT
            reasons += [line] if in_an_error_of_several_lines else []
            continue
        reasons += [reason] if (reason := _reason_in(line=line)) is not None else []
        in_an_error_of_several_lines = re.fullmatch(pattern=ERROR_LINE, string=line) is not None and not line.endswith(DEBUG_HINT)
    return reasons


def _reason_in(line: str) -> str | None:
    log_line = LogLine.of_text(text=line)
    if log_line is not None:
        return log_line.message if log_line.is_an_error() else None
    # the last line of a traceback or a crash of Python
    reason_pattern = rf"[A-Za-z_][\w.]*(Error|Exception)\b.*|Fatal Python error: .*|{ERROR_LINE}"
    return line if re.fullmatch(pattern=reason_pattern, string=line) else None
