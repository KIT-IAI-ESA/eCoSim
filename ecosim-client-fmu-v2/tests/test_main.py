import threading
from pathlib import Path

import pytest
from ecosim_client_fmu_v2.main import main
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import fmu2_model_path, resource_path_file
from ecosim_test_common.test_data.single_connection_server import SingleConnectionServer


@skip_unless_fmpy_loads(fmu2_model_path())
def test_exits_with_the_failed_run_exit_code_when_the_server_closes_mid_run(esp_monkey_patch: ESPMonkeyPatch) -> None:
    server = SingleConnectionServer.listen()
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_sys_arg("--config-file", str(resource_path_file("integration/models/fmu2/configs/feedthrough.ini")))
    esp_monkey_patch.set_sys_arg("--server-host", server.address().ip)
    esp_monkey_patch.set_sys_arg("--server-port", str(server.address().port))
    esp_monkey_patch.set_sys_arg("--debug")
    threading.Thread(target=server.serve_and_close, kwargs={"message_types": [MessageType.SIMULATION_START]}, daemon=True).start()

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE


def test_a_missing_fmu_file_ends_in_one_line_without_a_retry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    config_file = tmp_path / "preferences.ini"
    config_file.write_text(
        "[server]\nip = localhost\nport = 1234\n[simulator]\nsimulator_name = house\nmodel_name = house\ntype = fmu_2\n"
        + "fmc_file = [house.fmc]\n[fmu]\nfmu_file = [house.fmu]\n",
        encoding="utf-8",
    )
    (tmp_path / "house.fmc").write_text('{"inputs": [], "outputs": []}', encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=["--config-file", str(config_file)])

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert capsys.readouterr().err.splitlines()[-1].startswith(f"ecosim-client-fmu-v2: error: No such file or directory: {tmp_path / 'house.fmu'}")
    assert "Trying to reload" not in caplog.text
