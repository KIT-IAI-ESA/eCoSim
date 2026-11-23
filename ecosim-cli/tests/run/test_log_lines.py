from pathlib import Path

from ecosim.run.log_line import LogLine
from ecosim.run.reason_lines import reason_lines
from ecosim.run.server_log_follower import ServerLogFollower, line_to_show
from ecosim_common.tech.one_line_errors import DEBUG_HINT

from tests.run.log_lines import log_line


def shown_lines(log_file: Path, shows_warnings: bool) -> list[str]:
    log_lines = ServerLogFollower(log_file=log_file, read_up_to=0).new_log_lines()
    return [line for log_line in log_lines if (line := line_to_show(log_line=log_line, shows_warnings=shows_warnings)) is not None]


def test_the_line_pattern_reads_the_log_format_of_ecosim_common() -> None:
    assert LogLine.of_text(text=log_line(level="WARNING", logger="Server", message="Client house#hous: no simulator")) == LogLine(
        level="WARNING",
        logger="Server",
        message="Client house#hous: no simulator",
    )


def test_progress_and_warning_lines_of_the_server_are_shown(tmp_path: Path) -> None:
    log_file = tmp_path / "server.log"
    lines = [
        log_line(level="INFO", logger="Server", message="Starting server"),
        log_line(level="INFO", logger="Progress", message="Step 10 of 100"),
        log_line(level="WARNING", logger="Server", message="slow"),
    ]
    log_file.write_text("\n".join([*lines, "  a line of a traceback", ""]), encoding="utf-8")

    assert shown_lines(log_file=log_file, shows_warnings=True) == ["Step 10 of 100", "server: slow"]


def test_warnings_are_left_out_once_a_stop_has_begun(tmp_path: Path) -> None:
    log_file = tmp_path / "server.log"
    lines = [log_line(level="ERROR", logger="Server", message="Lost client"), log_line(level="INFO", logger="Progress", message="Step 10 of 100")]
    log_file.write_text("\n".join([*lines, ""]), encoding="utf-8")

    assert shown_lines(log_file=log_file, shows_warnings=False) == ["Step 10 of 100"]


def test_a_line_that_is_still_written_is_read_at_the_next_call(tmp_path: Path) -> None:
    log_file = tmp_path / "server.log"
    follower = ServerLogFollower(log_file=log_file, read_up_to=0)
    line = log_line(level="INFO", logger="Progress", message="Step 10 of 100")
    log_file.write_text(line[:30], encoding="utf-8")
    lines_of_the_first_call = follower.new_log_lines()
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"{line[30:]}\n")

    assert lines_of_the_first_call == []
    assert follower.new_log_lines() == [LogLine.of_text(text=line)]


def test_the_reason_of_a_failed_client_is_its_errors_and_the_end_of_its_traceback(tmp_path: Path) -> None:
    log_file = tmp_path / "house.log"
    logged_error = "The connection to the server ended before the simulation was stopped."
    last_line = f"ecosim-client-fmu-v2: error: KeyError: 'weatherBus_TDryBull' {DEBUG_HINT}"
    lines = [
        log_line(level="INFO", logger="Client", message="Starting"),
        log_line(level="ERROR", logger="Client", message=logged_error),
        "Traceback (most recent call last):",
        '  File "client.py", line 12, in step',
        "KeyError: 'weatherBus_TDryBull'",
        last_line,
    ]
    log_file.write_text("\n".join(lines), encoding="utf-8")

    assert reason_lines(log_file=log_file, start=0) == [logged_error, "KeyError: 'weatherBus_TDryBull'", last_line]


def test_the_reason_of_a_failed_server_has_every_line_of_its_error(tmp_path: Path) -> None:
    log_file = tmp_path / "server.log"
    lines = [
        "ecosim-server: error: The simulation config has invalid connections:",
        "- simulator 'house', interface 'weatherBus_TDryBul': simulator 'weather' has no interface 'weatherBus.TDryBul'.",
        DEBUG_HINT,
    ]
    log_file.write_text("\n".join(lines), encoding="utf-8")

    assert reason_lines(log_file=log_file, start=0) == lines[:2]


def test_a_log_without_errors_gives_its_last_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "house.log"
    log_file.write_text("\n".join(f"line {number}" for number in range(1, 9)), encoding="utf-8")

    assert reason_lines(log_file=log_file, start=0, count=3) == ["line 6", "line 7", "line 8"]


def test_the_reason_leaves_out_the_errors_of_an_earlier_run_in_the_same_log(tmp_path: Path) -> None:
    log_file = tmp_path / "house.log"
    earlier_run = f"{log_line(level='ERROR', logger='Client', message='an error of the earlier run')}\n"
    log_file.write_text(f"{earlier_run}line of this run\n", encoding="utf-8")

    assert reason_lines(log_file=log_file, start=len(earlier_run.encode())) == ["line of this run"]
