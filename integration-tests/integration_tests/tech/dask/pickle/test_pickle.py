import distributed
from cloudpickle import cloudpickle
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources.resource_utils import resource_path_file


def test_simulation_config(dask_client: distributed.Client) -> None:
    config = SimulationConfig.of_config_file_and_params(
        resource_path_file("fmu_v2/models/house/simulation.json"),
        steps=1,
    )
    cloudpickle.dumps(config)
