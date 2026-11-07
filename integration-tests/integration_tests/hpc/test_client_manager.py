from __future__ import annotations

import distributed
from _pytest.capture import CaptureFixture
from ecosim_hpc.client_manager import ClientManager
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from integration_tests.hpc.hpc_data import client_manager_config, fmu_files, simulation_config


@skip_unless_fmpy_loads(*fmu_files())
def test_client_manager_start_clients(
    dask_client: distributed.Client,
    capsys: CaptureFixture[str],
) -> None:
    manager = ClientManager(client_manager_config())
    manager.clients_start(simulation_config())

    for key, value in manager.client_dict.items():
        assert value.client_id == key
        assert value.is_boot_strapping_done.wait(timeout=4)
    for key, value in manager.client_dict.items():
        assert value.was_started_event.wait(timeout=2)  # type: ignore[union-attr] # at this point, was_started_event is not 'None'
