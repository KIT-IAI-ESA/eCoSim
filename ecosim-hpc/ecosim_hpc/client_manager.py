from typing import Any, Callable, override

import dask.distributed as dd
from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_pyro5.pyro_client import PyroClient
from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import ClientConfigOverride, SimulatorConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_client_state import HPCClientState
from ecosim_server.config.simulation_config import SimulationConfig
from fmpy import read_model_description


class ClientManager(ShutdownListener):
    logger = ESPLogger("ClientManager")

    def __init__(
        self,
        config: ClientManagerConfig,
    ):
        ShutdownManager().register_listener(self)
        self._config = config
        self.client_dict: ESPMap[str, HPCClientState] = ESPMap.dask()

    def clients_start(
        self,
        simulation_config: SimulationConfig,
    ) -> None:
        dask_client: dd.Client = dd.get_client()
        dask_client_ip = dask_client.scheduler_info()["address"].split(":")[1].strip("//")  # gets IP for dask scheduler
        for simulation in simulation_config.clients:
            self.client_dict[simulation.model_name] = HPCClientState(
                simulator_name=simulation.model_name,
                config_override=ClientConfigOverride(
                    server_host=self._config.host,
                    server_port=self._config.port,
                    communication_protocol=CommunicationProtocol.DASK,
                ),
            )
        for path in self._config.simulator_dir.iterdir():
            if not path.is_dir():
                continue
            if not any(path.glob("*.ini")):
                ClientManager.logger.debug(f"No ini file found in {path} -> skipping this directory.")
                continue
            simulator_config = ConfigParser([ini for ini in path.glob("*.ini")][0])
            simulator_name = SimulatorConfig.of_config_parser(simulator_config).model_name

            if simulator_name not in self.client_dict.keys():
                ClientManager.logger.warning(f"Simulator {simulator_name} not found in client_dict.")
                continue
            with self.client_dict.transaction() as clients:
                clients[simulator_name].config_parser = simulator_config

            simulator_path = path
            if any(simulator_path.glob("*.py")):  # Pyro5 Client first to ensure runs on same node as localhost
                # Find worker that is on the same node as the scheduler
                workers: Any | None = None
                for core in dask_client.ncores().keys():
                    if dask_client_ip in core:
                        workers = core  # Ensures Pyro client runs on same node as localhost
                        break
                dask_client.sync(
                    client_submit,
                    client_function=PyroClient,
                    client_states=self.client_dict,
                    state=self.client_dict[simulator_name],
                    workers=workers,
                )

            for fmu_file in simulator_path.glob("*.fmu"):
                fmu_description = read_model_description(fmu_file)
                if fmu_description.fmiVersion == "3.0":
                    if simulator_name in self.client_dict.keys():
                        dask_client.sync(
                            client_submit,
                            client_function=FMU3Client,
                            client_states=self.client_dict,
                            state=self.client_dict[simulator_name],
                        )
                elif fmu_description.fmiVersion == "2.0":
                    if simulator_name in self.client_dict.keys():
                        dask_client.sync(
                            client_submit,
                            client_function=FMU2Client,
                            client_states=self.client_dict,
                            state=self.client_dict[simulator_name],
                        )
                else:
                    ClientManager.logger.error("Unable to load %s. FMU V1 format not supported.", fmu_file)

            if any(simulator_path.glob("*.m")):
                from ecosim_client_matlab.matlab_client import MatlabClient

                if simulator_name in self.client_dict.keys():
                    dask_client.sync(
                        client_submit,
                        client_function=MatlabClient,
                        client_states=self.client_dict,
                        state=self.client_dict[simulator_name],
                    )

    @override
    def on_app_shutdown(self) -> None:
        dask_client = dd.get_client()
        dask_client.close()


async def client_submit(
    client_function: Callable[[ConfigParser, ClientConfigOverride], Client],
    client_states: ESPMap[str, HPCClientState],
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
    client_states: ESPMap[str, HPCClientState],
    state: HPCClientState,
) -> None:
    dd.get_client()
    dd.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
    simulator_client = client_function(
        state.config_parser,  # type: ignore[arg-type] # at this point, config_parser is not 'None'
        state.config_override,
    )
    with client_states.transaction() as clients:
        clients[state.simulator_name].was_started_event = simulator_client.was_started_event()
    client_states[state.simulator_name].is_boot_strapping_done.set()
    simulator_client.start()
    simulator_client.wait_until_finished()
    dd.rejoin()
