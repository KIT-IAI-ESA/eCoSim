from pathlib import Path

import distributed
import pytest
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path

from integration_tests.hpc.hpc_client_modules import ClientKind, write_broken_fmu2_module, write_client_module
from integration_tests.hpc.hpc_data import single_client_simulation_config

_FMU_FILES = {ClientKind.FMU2: fmu2_model_path(), ClientKind.FMU3: fmu3_model_path()}


@pytest.mark.parametrize(
    "kind",
    [pytest.param(kind, marks=skip_unless_fmpy_loads(_FMU_FILES[kind])) if kind in _FMU_FILES else kind for kind in ClientKind],
    ids=lambda kind: kind.value,
)
def test_client_manager_starts_every_client_kind(
    dask_client: distributed.Client,
    tmp_path: Path,
    kind: ClientKind,
) -> None:
    client_id = write_client_module(tmp_path, kind)
    manager = ClientManager(ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))

    manager.clients_start(single_client_simulation_config(client_id))

    state = manager.client_dict[client_id]
    # the client is created on a dask worker - if that fails, the bootstrapping never ends
    assert state.is_boot_strapping_done.wait(timeout=30), f"the {kind.value} client was not created"
    assert manager.client_dict[client_id].was_started_event.wait(timeout=10)  # type: ignore[union-attr] # set with the bootstrapping


@skip_unless_fmpy_loads(fmu2_model_path())
def test_client_manager_starts_an_fmu_that_fails_the_schema(
    dask_client: distributed.Client,
    tmp_path: Path,
) -> None:
    client_id = write_broken_fmu2_module(simulator_dir=tmp_path)
    manager = ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))

    manager.clients_start(simulation_config=single_client_simulation_config(client_id=client_id))

    assert manager.client_dict[client_id].is_boot_strapping_done.wait(timeout=30)
