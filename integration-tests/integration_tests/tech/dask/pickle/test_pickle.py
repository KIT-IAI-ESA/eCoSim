import distributed
from cloudpickle import cloudpickle
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.simulation.interface_value_history import InterfaceValueHistory
from ecosim_test_common.tech.db.repositories_in_memory import RepositoriesInMemory
from integration_tests.tech.resource_utils import resource_path_file


def test_pickle_value_history_with_dask_variable(dask_client: distributed.Client) -> None:
    repositories = RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK)
    history = InterfaceValueHistory(
        _repositories=repositories,
        _simulation_config=SimulationConfig.of_config_file_and_params(
            resource_path_file("models/houses/simulation.json"),
            steps=1,
        ),
        _entries=ESPMap.of_type(ESPStructureType.DASK_VARIABLE),
        _entries_queue=ESPQueue.of_type(ESPStructureType.DASK_VARIABLE),
    )
    cloudpickle.dumps(history)


# def test_pickle_value_history_with_dask_actor(dask_client: distributed.Client) -> None:
#     history = InterfaceValueHistory(
#         _repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
#         _simulation_config=SimulationConfig.of_config_file_and_params(
#             resource_path_file("models/houses/simulation.json"),
#             steps=1,
#         ),
#         _entries=ESPMap.of_type(ESPStructureType.DASK_ACTOR),
#     )
#     cloudpickle.dumps(history)


def test_simulation_config(dask_client: distributed.Client) -> None:
    config = SimulationConfig.of_config_file_and_params(
        resource_path_file("models/houses/simulation.json"),
        steps=1,
    )
    cloudpickle.dumps(config)


def test_repositories_in_memory(dask_client: distributed.Client) -> None:
    cloudpickle.dumps(RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK))
