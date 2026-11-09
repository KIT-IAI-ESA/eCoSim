import dask.distributed as distributed
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from integration_tests.hpc.hpc_data import client_manager_config, fmu_files, server_config, simulation_config
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory


# the server runs in a thread of its own - without this its death would only be reported as a warning
@pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")
@skip_unless_fmpy_loads(*fmu_files())
def test_hpc_main_process(dask_client: distributed.Client) -> None:
    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config(),
        simulation_config=simulation_config(),
        client_manager_config=client_manager_config(),
        repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
    )
