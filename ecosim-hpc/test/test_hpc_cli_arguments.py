from _pytest.capture import CaptureFixture
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.system_arguments import overwrite_system_argument
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch


def test_communication_protocol() -> None:
    overwrite_system_argument("--simulator-dir", "/path/to/simulator")
    overwrite_system_argument("--simulation-config", "/path/to/simulation/config")
    overwrite_system_argument("--server-config", "/path/to/server/config")
    overwrite_system_argument("--steps", "1000")

    cli_arguments = HPCServerCliArguments()
    assert cli_arguments.communication_protocol() == CommunicationProtocol.DASK


def test_cli_arguments_within_sql_alchemy(remove_pytest_variables: None, capsys: CaptureFixture[str], esp_monkey_patch: ESPMonkeyPatch) -> None:
    esp_monkey_patch.set_sys_arg("--simulator-dir", "/path/to/simulator")
    esp_monkey_patch.set_sys_arg("--simulation-config", "/path/to/simulation/config")
    esp_monkey_patch.set_sys_arg("--server-config", "/path/to/server/config")
    esp_monkey_patch.set_sys_arg("--steps", "1000")
    esp_monkey_patch.set_sys_arg("--port", "1000")

    from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base

    assert SimControlDB_Base is not None

    assert capsys.readouterr().err == ""
    assert capsys.readouterr().out == ""
