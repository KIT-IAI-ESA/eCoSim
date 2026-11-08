import threading

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
    threading.Thread(target=server.serve, kwargs={"message_types": [MessageType.SIMULATION_START]}, daemon=True).start()

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == ShutdownManager.FAILED_RUN_EXIT_CODE
