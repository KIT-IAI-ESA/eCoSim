from __future__ import annotations

import distributed
from _pytest.capture import CaptureFixture
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common import ESPMonkeyPatch
from integration_tests.tech import resource_utils


def test_client_manager_start_clients(
    dask_client: distributed.Client,
    esp_monkey_patch: ESPMonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    esp_monkey_patch.set_hpc_cli_sys_args(
        simulator_dir=resource_utils.resource_path_file_str("hpc/modules"),
        simulation_config_file=resource_utils.resource_path_file_str("hpc/modules/simulation.json"),
        server_config_file=resource_utils.resource_path_file_str("hpc/modules/preferences.ini"),
        steps="10",
    )

    cli_args = HPCServerCliArguments(ignore_unknown_arguments=True)
    simulation_config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=cli_args.simulation_config(),
        steps=10,
    )

    manager = ClientManager(cli_args)
    manager.clients_start(simulation_config)

    for key, value in manager.client_dict.items():
        assert value.simulator_name is not None
        assert value.is_boot_strapping_done.wait(timeout=4)
    for key, value in manager.client_dict.items():
        assert value.was_started_event.wait(timeout=2)  # type: ignore[union-attr] # at this point, was_started_event is not 'None'
