from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_matlab.matlab_client import MatlabClient
from ecosim_common.client.client import Client
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.cli_arguments import CLIArgumentsHPC
from ecosim_server.config.simulation_config import SimulationConfig

from pathlib import Path
from fmpy import read_model_description
import dask.distributed as dd
from typing import Any, override


class ClientManager(ShutdownListener):
    logger = ESPLogger("ClientManager")

    def __init__(
        self,
        server_args: CLIArgumentsHPC,
    ):
        ShutdownManager().register_listener(self)
        self._server_args = server_args
        self._modules_path = Path(server_args._args.simulator_dir)

    def clients_start(
        self,
        simulation_config: SimulationConfig,
    ) -> None:

        dask_client: dd.Client = dd.get_client()
        client_dict: dict[str, Any] = {}
        for simulation in simulation_config.clients:
            client_dict[simulation.model_name] = None
        for path in self._modules_path.iterdir():
            simulator_path = path
            for simulator in simulator_path.glob("*.fmu"):
                simulator_config = ConfigParser([ini for ini in simulator.parent.glob("*.ini")][0])
                fmu_description = read_model_description(simulator)
                if fmu_description.fmiVersion == "3.0":
                    fmu3_client = FMU3Client(
                        config_parser=simulator_config,
                        config_override=ClientConfigOverride(
                            server_host=self._server_args._args.host,
                            server_port=self._server_args._args.port,
                        ),
                        dask_connection=True,
                    )
                    if fmu3_client._client_config.simulator_config().model_name in client_dict.keys():
                        future = dask_client.submit(self.client_run, fmu3_client)
                        client_dict[fmu3_client._client_config.simulator_config().model_name] = future
                        dd.fire_and_forget(future)
                elif fmu_description.fmiVersion == "2.0":
                    fmu2_client = FMU2Client(
                        config_parser=simulator_config,
                        config_override=ClientConfigOverride(
                            server_host=self._server_args._args.host,
                            server_port=self._server_args._args.port,
                        ),
                        dask_connection=True,
                    )
                    if fmu2_client._client_config.simulator_config().model_name in client_dict.keys():
                        future = dask_client.submit(self.client_run, fmu2_client)
                        client_dict[fmu2_client._client_config.simulator_config().model_name] = future
                        dd.fire_and_forget(future)
                else:
                    ClientManager.logger.error(f"Unable to load {simulator}. FMU V1 format not supported.")
            for simulator in simulator_path.glob("*.m"):
                matlab_client = MatlabClient(
                    config_parser=simulator_config,
                    config_overrides=ClientConfigOverride(
                        server_host=self._server_args._args.host,
                        server_port=self._server_args._args.port,
                    ),
                    dask_connection=True,
                )
                if matlab_client._client_config.simulator_config().model_name in client_dict.keys():
                    future = dask_client.submit(self.client_run, matlab_client)
                    client_dict[matlab_client._client_config.simulator_config().model_name] = future
                    dd.fire_and_forget(future)

    @override
    def on_app_shutdown(self) -> None:
        dask_client = dd.get_client()
        dask_client.close()
        # dask_client.shutdown()

    @staticmethod
    def client_run(client: Client) -> None:
        client.start()
        client.wait_until_finished()
