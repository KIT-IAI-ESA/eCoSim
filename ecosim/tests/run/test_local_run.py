import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from ecosim.run.local_run import LocalRun, RunOutcome
from ecosim.run.run_process import ProcessToStart
from ecosim.run.run_watch import RunEnd, RunWatch
from ecosim_common.tech.shutdown_manager import SIGNAL_GRACE_IN_SECONDS, ShutdownManager
from ecosim_server.failure_texts import LOST_CLIENTS_PREFIX, LOST_CLIENTS_SUFFIX, RUN_FAILED_PREFIX
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS

from tests.run.fake_run_process import FakeRunProcess, local_run_in_a_subprocess
from tests.run.log_lines import log_line

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the fake processes handle POSIX signals")


def executed(local_run: LocalRun, directory: Path) -> RunOutcome:
    return local_run.execute(working_directory=directory, environment=dict(os.environ))


def started(local_run: LocalRun, directory: Path) -> RunWatch:
    watch = local_run.start(working_directory=directory, environment=dict(os.environ))
    FakeRunProcess.wait_until_ready(log_files=[process.log_file for process in watch.processes()])
    return watch


def exit_codes(watch: RunWatch) -> list[int]:
    return [process.exit_code() for process in watch.processes()]


def test_the_first_failing_process_stops_the_others(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=FakeRunProcess().to_start(name="server", directory=tmp_path),
        clients=[
            FakeRunProcess(exit_code=3, run_time_in_seconds=1).to_start(name="house", directory=tmp_path),
            FakeRunProcess().to_start(name="weather", directory=tmp_path),
        ],
    )
    watch = started(local_run=local_run, directory=tmp_path)

    outcome = local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert outcome.exit_code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert exit_codes(watch=watch) == [ShutdownManager.TERMINATE_EXIT_CODE, 3, ShutdownManager.TERMINATE_EXIT_CODE]


def test_a_client_that_ends_normally_stops_nothing(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=FakeRunProcess(run_time_in_seconds=2).to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess(run_time_in_seconds=0).to_start(name="house", directory=tmp_path)],
    )

    outcome = executed(local_run=local_run, directory=tmp_path)

    assert outcome.end is RunEnd.FINISHED
    assert outcome.run_time_in_seconds >= 2


def test_a_server_that_fails_on_its_own_ends_the_run_with_its_exit_code(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=FakeRunProcess(exit_code=5, run_time_in_seconds=0).to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess().to_start(name="house", directory=tmp_path)],
    )

    assert executed(local_run=local_run, directory=tmp_path).exit_code == 5


def test_a_ctrl_c_stops_every_process_with_the_interrupt_exit_code(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=FakeRunProcess().to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess().to_start(name="house", directory=tmp_path)],
    )
    watch = started(local_run=local_run, directory=tmp_path)

    watch.on_stop_signal(interrupted=True, received_at=time.monotonic())
    outcome = local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert outcome.end is RunEnd.INTERRUPTED
    assert [outcome.exit_code, *exit_codes(watch=watch)] == [ShutdownManager.INTERRUPT_EXIT_CODE] * 3


def test_a_ctrl_c_is_an_interrupt_also_when_the_processes_end_as_terminated(tmp_path: Path) -> None:
    stopped_as_on_windows = FakeRunProcess(exit_code_of_a_stop=ShutdownManager.TERMINATE_EXIT_CODE)
    local_run = LocalRun(
        server=stopped_as_on_windows.to_start(name="server", directory=tmp_path),
        clients=[stopped_as_on_windows.to_start(name="house", directory=tmp_path)],
    )
    watch = started(local_run=local_run, directory=tmp_path)

    watch.on_stop_signal(interrupted=True, received_at=time.monotonic())
    outcome = local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert outcome.exit_code == ShutdownManager.INTERRUPT_EXIT_CODE


def test_a_second_ctrl_c_within_the_grace_time_is_the_same_ctrl_c(tmp_path: Path) -> None:
    # a kill would come before the processes have stopped
    slow_to_stop = FakeRunProcess(stop_time_in_seconds=1)
    local_run = LocalRun(
        server=slow_to_stop.to_start(name="server", directory=tmp_path),
        clients=[slow_to_stop.to_start(name="house", directory=tmp_path)],
    )
    watch = started(local_run=local_run, directory=tmp_path)
    first_ctrl_c_at = time.monotonic()

    watch.on_stop_signal(interrupted=True, received_at=first_ctrl_c_at)
    watch.on_stop_signal(interrupted=True, received_at=first_ctrl_c_at + SIGNAL_GRACE_IN_SECONDS / 2)
    local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert exit_codes(watch=watch) == [ShutdownManager.INTERRUPT_EXIT_CODE] * 2


def test_a_second_ctrl_c_after_the_grace_time_kills_every_process(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=FakeRunProcess(ignores_the_stop=True).to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess(ignores_the_stop=True).to_start(name="house", directory=tmp_path)],
        stop_timeout_in_seconds=60,
    )
    watch = started(local_run=local_run, directory=tmp_path)
    first_ctrl_c_at = time.monotonic()

    watch.on_stop_signal(interrupted=True, received_at=first_ctrl_c_at)
    watch.on_stop_signal(interrupted=True, received_at=first_ctrl_c_at + SIGNAL_GRACE_IN_SECONDS + 1)
    outcome = local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert exit_codes(watch=watch) == [-signal.SIGKILL] * 2
    assert outcome.exit_code == ShutdownManager.INTERRUPT_EXIT_CODE


def test_a_terminate_signal_stops_every_process_with_the_terminate_exit_code(tmp_path: Path) -> None:
    local_run = LocalRun(
        server=FakeRunProcess().to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess().to_start(name="house", directory=tmp_path)],
    )
    watch = started(local_run=local_run, directory=tmp_path)

    watch.on_stop_signal(interrupted=False, received_at=time.monotonic())
    outcome = local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert outcome.end is RunEnd.TERMINATED
    assert [outcome.exit_code, *exit_codes(watch=watch)] == [ShutdownManager.TERMINATE_EXIT_CODE] * 3


@pytest.mark.parametrize(
    "signal_number, exit_code",
    [
        (signal.SIGINT, ShutdownManager.INTERRUPT_EXIT_CODE),
        (signal.SIGTERM, ShutdownManager.TERMINATE_EXIT_CODE),
        (signal.SIGHUP, ShutdownManager.TERMINATE_EXIT_CODE),
    ],
    ids=["ctrl-c", "terminate", "closed terminal"],
)
def test_a_real_signal_stops_a_run_in_another_process(tmp_path: Path, signal_number: int, exit_code: int) -> None:
    server = FakeRunProcess().to_start(name="server", directory=tmp_path)
    run = local_run_in_a_subprocess(server=server, directory=tmp_path)
    try:
        FakeRunProcess.wait_until_ready(log_files=[server.log_file])

        run.send_signal(signal_number)

        assert run.wait(timeout=WAIT_TIMEOUT_IN_SECONDS) == exit_code
    finally:
        run.kill()


def test_the_lost_client_is_shown_first_when_every_process_ends_at_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    message = f"{RUN_FAILED_PREFIX}{LOST_CLIENTS_PREFIX}weather#weather{LOST_CLIENTS_SUFFIX}waiting for all clients"
    lost_weather = log_line(level="ERROR", logger="Server", message=message)
    local_run = LocalRun(
        server=FakeRunProcess(exit_code=1, run_time_in_seconds=0, last_line=lost_weather).to_start(name="server", directory=tmp_path),
        clients=[
            FakeRunProcess(exit_code=1, run_time_in_seconds=0).to_start(name="house", directory=tmp_path),
            FakeRunProcess(exit_code=1, run_time_in_seconds=0).to_start(name="weather", directory=tmp_path),
        ],
        # every process ends between two polls
        poll_interval_in_seconds=3,
    )

    executed(local_run=local_run, directory=tmp_path)

    [stopped] = [line for line in capsys.readouterr().out.splitlines() if " stopped with exit code " in line]
    assert stopped.startswith("weather stopped with exit code 1.")


def test_the_failed_server_is_shown_when_the_clients_end_at_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    local_run = LocalRun(
        server=FakeRunProcess(exit_code=5, run_time_in_seconds=0).to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess(exit_code=1, run_time_in_seconds=0).to_start(name="house", directory=tmp_path)],
        poll_interval_in_seconds=3,
    )

    outcome = executed(local_run=local_run, directory=tmp_path)

    assert outcome.exit_code == 5
    assert "server stopped with exit code 5." in capsys.readouterr().out


def test_a_restore_shows_no_line_of_the_earlier_run_in_the_same_logs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    earlier_server_lines = [
        log_line(level="INFO", logger="Progress", message="Step 1,555 of 20,000 of the earlier run"),
        log_line(level="WARNING", logger="Server", message="a warning of the earlier run"),
    ]
    (tmp_path / "server.log").write_text("\n".join([*earlier_server_lines, ""]), encoding="utf-8")
    (tmp_path / "house.log").write_text(f"{log_line(level='ERROR', logger='Client', message='an error of the earlier run')}\n", encoding="utf-8")
    local_run = LocalRun(
        server=FakeRunProcess().to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess(exit_code=3, run_time_in_seconds=1).to_start(name="house", directory=tmp_path)],
    )

    executed(local_run=local_run, directory=tmp_path)

    output = capsys.readouterr().out
    assert "house stopped with exit code 3." in output
    assert "earlier run" not in output


def test_a_process_that_ignores_the_stop_is_killed_after_the_time_to_stop(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    local_run = LocalRun(
        server=FakeRunProcess(ignores_the_stop=True).to_start(name="server", directory=tmp_path),
        clients=[FakeRunProcess(exit_code=1, run_time_in_seconds=1).to_start(name="house", directory=tmp_path)],
        stop_timeout_in_seconds=1,
    )
    watch = started(local_run=local_run, directory=tmp_path)

    local_run.wait_for_the_end(watch=watch, received_signals=[])

    assert watch.server.exit_code() == -signal.SIGKILL
    assert "server did not stop within 1.0 s. It was killed." in capsys.readouterr().out


def test_a_client_that_cannot_start_leaves_no_process_running(tmp_path: Path) -> None:
    # the folder on the command line of the server finds its process
    server = FakeRunProcess().to_start(name="server", directory=tmp_path)
    local_run = LocalRun(
        server=ProcessToStart(name="server", command=[*server.command, str(tmp_path)], log_file=server.log_file),
        clients=[ProcessToStart(name="house", command=[str(tmp_path / "no-such-program")], log_file=tmp_path / "house.log")],
    )

    with pytest.raises(FileNotFoundError):
        executed(local_run=local_run, directory=tmp_path)

    assert no_process_has_within_two_seconds(text=str(tmp_path))


def no_process_has_within_two_seconds(text: str) -> bool:
    for _ in range(20):
        if subprocess.run(["pgrep", "-f", "--", text], check=False, capture_output=True).returncode == 1:
            return True
        time.sleep(0.1)
    return False
