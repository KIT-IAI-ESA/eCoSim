import threading
import traceback
from pathlib import Path

import ecosim_test_common.test_data.python_models
import pytest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.resources.resource_utils import python_room_config_path
from ecosim_test_common.test_data.single_connection_server import SingleConnectionServer

from ecosim_client_python.main import main


def test_exits_with_the_failed_run_exit_code_when_the_server_closes_mid_run() -> None:
    server = SingleConnectionServer.listen()
    threading.Thread(target=server.serve_and_close, kwargs={"message_types": [MessageType.SIMULATION_START]}, daemon=True).start()
    server_address = server.address()

    with pytest.raises(SystemExit) as exit_info:
        main(
            passed_arguments=[
                *("--config-file", str(python_room_config_path())),
                *("--server-host", server_address.ip, "--server-port", str(server_address.port)),
                "--debug",
            ],
        )

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE


def _config_file_naming(model: str, folder: Path) -> Path:
    config_file = folder / "preferences.ini"
    config_file.write_text(
        "[server]\nip = localhost\nport = 1234\n[simulator]\nsimulator_name = room\nmodel_name = room\ntype = python\n"
        + f"fmc_file = [room.fmc]\n[python]\nmodel = {model}\n",
        encoding="utf-8",
    )
    (folder / "room.fmc").write_text('{"inputs": [], "outputs": []}', encoding="utf-8")
    return config_file


def test_a_misspelt_class_ends_in_one_line_that_names_the_class_meant(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_file = _config_file_naming(model="ecosim_test_common.test_data.python_models:DoublingModl", folder=tmp_path)

    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=["--config-file", str(config_file)])

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"ecosim-client-python: error: {ecosim_test_common.test_data.python_models.__file__} has no DoublingModl. Did you mean DoublingModel? "
        + "(run with --debug for the full traceback)"
    )


@pytest.mark.parametrize(
    ("module_name", "module_code", "what_failed"),
    [
        ("room_with_a_syntax_error", "class Room\n    pass\n", "its module was imported: expected ':' (room_with_a_syntax_error.py, line 1)"),
        ("room_dividing_by_zero", "class Room:\n    def __init__(self) -> None:\n        self.share = 1 / 0\n", "it was created: division by zero"),
    ],
    ids=["import", "creation"],
)
def test_an_error_in_the_code_of_the_model_ends_in_one_line_that_names_the_model(
    module_name: str,
    module_code: str,
    what_failed: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / f"{module_name}.py").write_text(module_code, encoding="utf-8")
    config_file = _config_file_naming(model=f"{module_name}:Room", folder=tmp_path)

    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=["--config-file", str(config_file)])

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"ecosim-client-python: error: The model {module_name}:Room failed while {what_failed} (run with --debug for the full traceback)"
    )


@pytest.mark.parametrize(
    ("module_name", "module_code", "error_type", "failed_code_line"),
    [
        ("heater_with_an_unknown_name", "power = unknown_name\n", ImportError, "line 1, in <module>"),
        ("heater_dividing_by_zero", "class Heater:\n    def __init__(self):\n        self.share = 1 / 0\n", RuntimeError, "line 3, in __init__"),
    ],
    ids=["import", "creation"],
)
def test_with_debug_an_error_of_the_model_keeps_the_traceback_of_the_model_code(
    module_name: str,
    module_code: str,
    error_type: type[Exception],
    failed_code_line: str,
    tmp_path: Path,
) -> None:
    module_file = tmp_path / f"{module_name}.py"
    module_file.write_text(module_code, encoding="utf-8")
    config_file = _config_file_naming(model=f"{module_name}:Heater", folder=tmp_path)

    with pytest.raises(error_type) as error_info:
        main(passed_arguments=["--config-file", str(config_file), "--debug"])

    shown_traceback = "".join(traceback.format_exception(error_info.value))
    assert f'File "{module_file}", {failed_code_line}' in shown_traceback
