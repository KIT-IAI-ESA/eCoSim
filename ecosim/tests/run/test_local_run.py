import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from ecosim.run.local_run import LocalRun, RunOutcome
from ecosim.run.run_part import PartToStart
from ecosim.run.run_watch import RunEnd
from ecosim_common.tech.shutdown_manager import SIGNAL_GRACE_IN_SECONDS
from ecosim_test_common.test_data.fake_run_part import FakeRunPart

from tests.run.log_lines import log_line

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the tests send POSIX signals to the test process")


def part(name: str, fake: FakeRunPart, folder: Path) -> PartToStart:
    return PartToStart(name=name, command=fake.command(), log_file=folder / f"{name}.log")


def executed(local_run: LocalRun, folder: Path) -> RunOutcome:
    return local_run.execute(working_folder=folder, environment=dict(os.environ))


def log_of(name: str, folder: Path) -> str:
    return (folder / f"{name}.log").read_text(encoding="utf-8")


def send_when_ready(signal_numbers: list[int], log_files: list[Path], seconds_between_signals: float = 0) -> None:
    """Sends the signals to this process, which runs the run, once every part handles them."""

    def send() -> None:
        # the line alone, since the command in the first line of the log has the word too
        while not all(log_file.is_file() and "ready" in log_file.read_text(encoding="utf-8").splitlines() for log_file in log_files):
            time.sleep(0.1)
        for signal_number in signal_numbers:
            os.kill(os.getpid(), signal_number)
            time.sleep(seconds_between_signals)

    threading.Thread(target=send, daemon=True).start()


def test_the_first_failing_part_stops_the_others(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(), folder=tmp_path),
        clients=[
            part(name="house", fake=FakeRunPart(exit_code=3, seconds=1), folder=tmp_path),
            part(name="weather", fake=FakeRunPart(), folder=tmp_path),
        ],
    )

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.FAILED, 1)
    assert "exit 44" in log_of(name="server", folder=tmp_path) and "exit 44" in log_of(name="weather", folder=tmp_path)
    assert "house stopped with exit code 3." in capsys.readouterr().out


def test_a_client_that_ends_normally_stops_nothing(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(seconds=2), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(seconds=0), folder=tmp_path)],
    )

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.FINISHED, 0)
    assert outcome.seconds >= 2


def test_a_server_that_fails_on_its_own_ends_the_run_with_its_exit_code(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(exit_code=5, seconds=0), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(), folder=tmp_path)],
    )

    assert executed(local_run=local_run, folder=tmp_path).exit_code == 5


def test_a_ctrl_c_stops_every_part_with_the_interrupt_exit_code(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(), folder=tmp_path)],
    )
    send_when_ready(signal_numbers=[signal.SIGINT], log_files=[tmp_path / "server.log", tmp_path / "house.log"])

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.INTERRUPTED, 33)
    assert "exit 33" in log_of(name="server", folder=tmp_path) and "exit 33" in log_of(name="house", folder=tmp_path)


def test_a_ctrl_c_ends_the_run_with_the_interrupt_exit_code_when_the_parts_end_with_the_terminate_exit_code(tmp_path: Path) -> None:
    # as on Windows, where every stop reaches the parts as a break signal
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(exit_code_of_a_stop=44), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(exit_code_of_a_stop=44), folder=tmp_path)],
    )
    send_when_ready(signal_numbers=[signal.SIGINT], log_files=[tmp_path / "server.log", tmp_path / "house.log"])

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.INTERRUPTED, 33)
    assert "exit 44" in log_of(name="server", folder=tmp_path)


def test_a_second_ctrl_c_within_the_grace_time_is_the_same_ctrl_c(tmp_path: Path) -> None:
    # parts that take a moment to stop, so a kill would come before their last line
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(seconds_to_stop=1), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(seconds_to_stop=1), folder=tmp_path)],
    )
    # a moment apart, since Python runs the handler once for a signal that comes twice before it runs
    send_when_ready(
        signal_numbers=[signal.SIGINT, signal.SIGINT],
        log_files=[tmp_path / "server.log", tmp_path / "house.log"],
        seconds_between_signals=0.2,
    )

    executed(local_run=local_run, folder=tmp_path)

    assert "exit 33" in log_of(name="server", folder=tmp_path) and "exit 33" in log_of(name="house", folder=tmp_path)


def test_a_second_ctrl_c_after_the_grace_time_kills_every_part(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(ignores_the_stop=True), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(ignores_the_stop=True), folder=tmp_path)],
        seconds_to_stop=60,
    )
    send_when_ready(
        signal_numbers=[signal.SIGINT, signal.SIGINT],
        log_files=[tmp_path / "server.log", tmp_path / "house.log"],
        seconds_between_signals=SIGNAL_GRACE_IN_SECONDS + 0.5,
    )

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.INTERRUPTED, 33)
    # long before the time to stop is over
    assert outcome.seconds < 30


@pytest.mark.parametrize("signal_number", [signal.SIGTERM, signal.SIGHUP], ids=["terminate", "hangup"])
def test_a_terminate_signal_or_a_closed_terminal_stops_every_part_with_the_terminate_exit_code(
    tmp_path: Path,
    signal_number: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local_run = LocalRun(server=part(name="server", fake=FakeRunPart(), folder=tmp_path), clients=[])
    send_when_ready(signal_numbers=[signal_number], log_files=[tmp_path / "server.log"])

    assert executed(local_run=local_run, folder=tmp_path).exit_code == 44
    assert "exit 44" in log_of(name="server", folder=tmp_path)
    assert "Ctrl-C" not in capsys.readouterr().out


def test_the_client_that_the_server_lost_is_named_when_the_parts_end_in_the_same_look(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lost_weather = log_line(level="ERROR", logger="Server", message="The run failed: Lost client weather#weather while waiting for all clients")
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(exit_code=1, seconds=0, last_line=lost_weather), folder=tmp_path),
        clients=[
            part(name="house", fake=FakeRunPart(exit_code=1, seconds=0), folder=tmp_path),
            part(name="weather", fake=FakeRunPart(exit_code=1, seconds=0), folder=tmp_path),
        ],
        # every part ends before the next look
        seconds_between_looks=3,
    )

    outcome = executed(local_run=local_run, folder=tmp_path)

    output = capsys.readouterr().out
    assert (outcome.end, outcome.exit_code) == (RunEnd.FAILED, 1)
    assert "weather stopped with exit code 1." in output and "house stopped" not in output
    assert "server: The run failed: Lost client weather#weather while waiting for all clients" in output


def test_the_server_is_named_when_it_fails_and_the_clients_end_in_the_same_look(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(exit_code=5, seconds=0), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(exit_code=1, seconds=0), folder=tmp_path)],
        seconds_between_looks=3,
    )

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.FAILED, 5)
    assert "server stopped with exit code 5." in capsys.readouterr().out


def test_a_restore_shows_no_line_of_the_earlier_run_in_the_same_logs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    earlier_server_lines = [
        log_line(level="INFO", logger="Progress", message="Step 1,555 of 20,000 of the earlier run"),
        log_line(level="WARNING", logger="Server", message="a warning of the earlier run"),
    ]
    (tmp_path / "server.log").write_text("\n".join([*earlier_server_lines, ""]), encoding="utf-8")
    (tmp_path / "house.log").write_text(f"{log_line(level='ERROR', logger='Client', message='an error of the earlier run')}\n", encoding="utf-8")
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(exit_code=3, seconds=1), folder=tmp_path)],
    )

    executed(local_run=local_run, folder=tmp_path)

    output = capsys.readouterr().out
    assert "house stopped with exit code 3." in output
    assert "earlier run" not in output


def test_a_part_that_ignores_the_stop_is_killed_after_the_time_to_stop(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    local_run = LocalRun(
        server=part(name="server", fake=FakeRunPart(ignores_the_stop=True), folder=tmp_path),
        clients=[part(name="house", fake=FakeRunPart(exit_code=1, seconds=1), folder=tmp_path)],
        seconds_to_stop=1,
    )

    outcome = executed(local_run=local_run, folder=tmp_path)

    assert (outcome.end, outcome.exit_code) == (RunEnd.FAILED, 1)
    assert "server did not stop within 1.0 s, so it was killed." in capsys.readouterr().out


def test_a_client_that_cannot_start_leaves_no_part_running(tmp_path: Path) -> None:
    # the folder on the command line of the server finds its process
    server = PartToStart(name="server", command=[*FakeRunPart().command(), str(tmp_path)], log_file=tmp_path / "server.log")
    local_run = LocalRun(
        server=server,
        clients=[PartToStart(name="house", command=[str(tmp_path / "no-such-program")], log_file=tmp_path / "house.log")],
    )

    with pytest.raises(FileNotFoundError):
        executed(local_run=local_run, folder=tmp_path)

    assert no_process_has_within_two_seconds(text=str(tmp_path))


def no_process_has_within_two_seconds(text: str) -> bool:
    for _ in range(20):
        if subprocess.run(["pgrep", "-f", "--", text], check=False, capture_output=True).returncode == 1:
            return True
        time.sleep(0.1)
    return False
