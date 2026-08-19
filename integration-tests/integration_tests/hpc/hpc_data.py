from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.cli_arguments import ServerConfigOverride
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from integration_tests.tech import resource_utils


def simulation_config() -> SimulationConfig:
    return SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_utils.resource_path_file("hpc/modules/simulation.json"),
        steps=10,
    )


def client_manager_config() -> ClientManagerConfig:
    return ClientManagerConfig(
        host="localhost",
        port=9090,
        simulator_dir=resource_utils.resource_path_file("hpc/modules"),
    )


def server_config() -> ServerConfig:
    return ServerConfig.of_file(
        resource_utils.resource_path_file("hpc/modules/preferences.ini"),
        config_override=ServerConfigOverride(
            communication_protocol=CommunicationProtocol.DASK,
            server_host=None,
            server_port=None,
        ),
    )
