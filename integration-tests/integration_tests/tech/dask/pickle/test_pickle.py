import distributed
from cloudpickle import cloudpickle
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.simulation.interface_value_history import InterfaceValueHistory
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory
from integration_tests.tech.resource_utils import resource_path_file


def test_pickle_value_history_for_protocol(dask_client: distributed.Client) -> None:
    history = InterfaceValueHistory(
        _parallel_lock=ParallelLock.for_protocol(
            CommunicationProtocol.DASK,
        ),
        _repositories=RepositoriesInMemory(),
        _simulation_config=SimulationConfig.of_config_file_and_params(
            resource_path_file("models/houses/simulation.json"),
            steps=1,
        ),
        _entries=ESPMap.of_type(ESPStructureType.DASK),
    )
    cloudpickle.dumps(history)


def test_simulation_config(dask_client: distributed.Client) -> None:
    config = SimulationConfig.of_config_file_and_params(
        resource_path_file("models/houses/simulation.json"),
        steps=1,
    )
    cloudpickle.dumps(config)


def test_repositories_in_memory(dask_client: distributed.Client) -> None:
    cloudpickle.dumps(RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK))
