import pytest
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch


@pytest.fixture(autouse=True)
def replace_pytest_arguments_with_hpc_command_line(esp_monkey_patch: ESPMonkeyPatch) -> None:
    """Under pytest, 'sys.argv' holds pytest's arguments, which 'HPCServerCliArguments' rejects as unknown."""
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()
