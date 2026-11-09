from datetime import datetime
from pathlib import Path

import distributed
import pytest
from ecosim_common.config.client_id import ClientID
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path

from integration_tests.hpc.hpc_client_modules import ClientKind, write_client_module

_FMU_FILES = {ClientKind.FMU2: fmu2_model_path(), ClientKind.FMU3: fmu3_model_path()}


def _simulation_config(model_name: str) -> SimulationConfig:
    client = ClientSimulatorConfig(
        simulator_name=model_name,
        model_name=model_name,
        interfaces=[],
        client_id=ClientID(model_name=model_name, simulator_name=model_name),
    )
    return SimulationConfig(
        clients=[client],
        start_date=datetime(2025, 1, 1),
        logical_delays=[],
        pace=1.0,
        steps=10,
        step_size_in_ms=1_000,
        restore=False,
    )


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
    model_name = write_client_module(tmp_path, kind)
    manager = ClientManager(ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))

    manager.clients_start(_simulation_config(model_name))

    state = manager.client_dict[model_name]
    # the client is created on a dask worker - if that fails, the bootstrapping never ends
    assert state.is_boot_strapping_done.wait(timeout=30), f"the {kind.value} client was not created"
    assert manager.client_dict[model_name].was_started_event.wait(timeout=10)  # type: ignore[union-attr] # set with the bootstrapping
