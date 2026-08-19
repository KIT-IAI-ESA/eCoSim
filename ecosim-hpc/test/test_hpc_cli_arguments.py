from _pytest.capture import CaptureFixture
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch


def test_communication_protocol(
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.set_hpc_cli_sys_args()

    cli_arguments = HPCServerCliArguments()
    assert cli_arguments.communication_protocol() == CommunicationProtocol.DASK


def test_cli_arguments_within_sql_alchemy(
    remove_pytest_variables: None,
    capsys: CaptureFixture[str],
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.set_hpc_cli_sys_args()

    from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base

    assert SimControlDB_Base is not None

    logs = capsys.readouterr()
    assert logs.err == ""
    assert logs.out == ""
