from typing import Callable, override

import dask.distributed as dd
from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_pyro5.pyro_client import PyroClient
from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.config.simulator_directory import SimulatorDirectory
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from ecosim_server.config.simulation_config import SimulationConfig

from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_client_state import HPCClientState


class ClientManager(ShutdownListener):
    logger = ESPLogger("ClientManager")

    def __init__(
        self,
        config: ClientManagerConfig,
    ):
        ShutdownManager().register_listener(self)
        self._config = config
        self.client_dict: ESPMap[ClientID, HPCClientState] = ESPMap.dask()

    def clients_start(
        self,
        simulation_config: SimulationConfig,
        dask_client_overwrite: dd.Client | None = None,
    ) -> None:
        dask_client = dask_client_overwrite or dd.get_client()
        simulator_directories = SimulatorDirectory.find_for_simulators(
            simulators_directory=self._config.simulator_dir,
            client_ids=[simulation.client_id for simulation in simulation_config.clients],
        )
        for client_id, simulator_directory in simulator_directories.items():
            self.client_dict[client_id] = HPCClientState(
                client_id=client_id,
                config_override=ClientConfigOverride(
                    server_host=self._config.host,
                    server_port=self._config.port,
                    communication_protocol=CommunicationProtocol.DASK,
                ),
                config_parser=simulator_directory.config_parser,
            )
            simulator_path = simulator_directory.path
            if any(simulator_path.glob("*.py")):
                dask_client.sync(
                    client_submit,
                    client_function=PyroClient.of,
                    client_states=self.client_dict,
                    state=self.client_dict[client_id],
                )

            for fmu_file in simulator_path.glob("*.fmu"):
                fmu_description = read_model_description(file=fmu_file)
                if fmu_description.fmiVersion == "3.0":
                    if client_id in self.client_dict.keys():
                        dask_client.sync(
                            client_submit,
                            client_function=FMU3Client.of,
                            client_states=self.client_dict,
                            state=self.client_dict[client_id],
                        )
                elif fmu_description.fmiVersion == "2.0":
                    if client_id in self.client_dict.keys():
                        dask_client.sync(
                            client_submit,
                            client_function=FMU2Client.create,
                            client_states=self.client_dict,
                            state=self.client_dict[client_id],
                        )
                else:
                    ClientManager.logger.error("Unable to load %s. FMU V1 format not supported.", fmu_file)

            if any(simulator_path.glob("*.m")):
                from ecosim_client_matlab.matlab_client import MatlabClient

                if client_id in self.client_dict.keys():
                    dask_client.sync(
                        client_submit,
                        client_function=MatlabClient.of,
                        client_states=self.client_dict,
                        state=self.client_dict[client_id],
                    )

    @override
    def on_app_shutdown(self) -> None:
        dask_client = dd.get_client()
        dask_client.close()


async def client_submit(
    client_function: Callable[[ConfigParser, ClientConfigOverride], Client],
    client_states: ESPMap[ClientID, HPCClientState],
    state: HPCClientState,
    workers: str | None = None,
) -> None:
    dask_client = dd.get_client()
    if workers:
        client_future = dask_client.submit(client_run, client_function, client_states, state, workers=workers)
        # ClientManager.logger.debug(f"{dask_client.scheduler_info()["address"]}")
        # ClientManager.logger.debug(f"{await dask_client.who_has(client_future)}")
    else:
        client_future = dask_client.submit(client_run, client_function, client_states, state)
    dd.fire_and_forget(client_future)


def client_run(
    client_function: Callable[[ConfigParser, ClientConfigOverride], Client],
    client_states: ESPMap[ClientID, HPCClientState],
    state: HPCClientState,
) -> None:
    dd.get_client()
    dd.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
    simulator_client = client_function(
        state.config_parser,
        state.config_override,
    )
    with client_states.transaction() as clients:
        clients[state.client_id].was_started_event = simulator_client.was_started_event()
    client_states[state.client_id].is_boot_strapping_done.set()
    simulator_client.start()
    simulator_client.wait_until_finished()
    dd.rejoin()
