import errno
import os

import pytest
from ecosim_common.tech.one_line_errors import DEBUG_HINT, exits_with_one_line_errors, one_line_message
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch
from ecosim_test_common.test_data.raising_main import RaisingMain


def _a_missing_file() -> FileNotFoundError:
    return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "server/simulaton.json")


def test_an_error_ends_in_one_line_on_stderr_and_the_failed_run_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    main = exits_with_one_line_errors(program_name="ecosim-test")(RaisingMain(error=_a_missing_file()))

    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=[])

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert capsys.readouterr().err == f"ecosim-test: error: No such file or directory: server/simulaton.json {DEBUG_HINT}\n"


def test_with_debug_the_error_itself_ends_the_program() -> None:
    main = exits_with_one_line_errors(program_name="ecosim-test")(RaisingMain(error=_a_missing_file()))

    with pytest.raises(FileNotFoundError):
        main(passed_arguments=["--debug"])


def test_without_passed_arguments_the_command_line_counts(esp_monkey_patch: ESPMonkeyPatch) -> None:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_sys_arg("--debug")
    raising_main = RaisingMain(error=_a_missing_file())

    with pytest.raises(FileNotFoundError):
        exits_with_one_line_errors(program_name="ecosim-test")(raising_main)()

    assert raising_main.passed_arguments == ["--debug"]


def test_the_exit_code_of_a_signal_stays() -> None:
    main = exits_with_one_line_errors(program_name="ecosim-test")(RaisingMain(error=SystemExit(ShutdownManager.INTERRUPT_EXIT_CODE)))

    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=[])

    assert exit_info.value.code == ShutdownManager.INTERRUPT_EXIT_CODE


def test_ctrl_c_is_not_turned_into_an_error_line(capsys: pytest.CaptureFixture[str]) -> None:
    main = exits_with_one_line_errors(program_name="ecosim-test")(RaisingMain(error=KeyboardInterrupt()))

    with pytest.raises(KeyboardInterrupt):
        main(passed_arguments=[])

    assert capsys.readouterr().err == ""


def test_a_message_of_several_lines_gets_the_hint_on_its_own_line(capsys: pytest.CaptureFixture[str]) -> None:
    error = RuntimeError("The simulation config has invalid connections:\n- simulator 'house', interface 'T_out': no connection")
    main = exits_with_one_line_errors(program_name="ecosim-test")(RaisingMain(error=error))

    with pytest.raises(SystemExit):
        main(passed_arguments=[])

    assert capsys.readouterr().err == f"ecosim-test: error: {error}\n{DEBUG_HINT}\n"


def test_a_key_error_shows_its_type() -> None:
    assert one_line_message(error=KeyError("setup")) == "KeyError: 'setup'"


def test_an_error_without_a_message_shows_its_type() -> None:
    assert one_line_message(error=TimeoutError()) == "TimeoutError"


def test_a_socket_error_drops_the_error_number() -> None:
    error = OSError(errno.EADDRINUSE, "Cannot listen on localhost:1234: Address already in use")

    assert one_line_message(error=error) == "Cannot listen on localhost:1234: Address already in use"
