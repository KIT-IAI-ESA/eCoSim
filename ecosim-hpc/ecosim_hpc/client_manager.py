from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_matlab.matlab_client import MatlabClient
from ecosim_client_pyro5.pyro_client import PyroClient
from ecosim_common.client.client import Client
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.client.config.client_config import ClientConfigOverride, SimulatorConfig
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.cli_arguments import CLIArgumentsHPC
from ecosim_server.config.simulation_config import SimulationConfig

from pathlib import Path
from fmpy import read_model_description
import dask.distributed as dd
from typing import Any, override, Callable


class ClientManager(ShutdownListener):
    logger = ESPLogger("ClientManager")

    def __init__(
        self,
        server_args: CLIArgumentsHPC,
    ):
        ShutdownManager().register_listener(self)
        self._server_args = server_args
        self._modules_path = Path(server_args._args.simulator_dir)
        self.client_dict: dict[str, Any] = {}

    def clients_start(
        self,
        simulation_config: SimulationConfig,
    ) -> None:

        dask_client: dd.Client = dd.get_client()
        dask_client_ip = dask_client.scheduler_info()["address"].split(":")[1].strip("//")  # gets IP for dask scheduler
        for simulation in simulation_config.clients:
            self.client_dict[simulation.model_name] = None
        for path in self._modules_path.iterdir():
            simulator_path = path
            args = {
                "config_override": ClientConfigOverride(
                    server_host=self._server_args._args.host,
                    server_port=self._server_args._args.port,
                ),
                "dask_connection": True,
            }
            for simulator in simulator_path.glob("*.fmu"):
                simulator_config = ConfigParser([ini for ini in simulator.parent.glob("*.ini")][0])
                simulator_name = SimulatorConfig.of_config_parser(simulator_config).model_name
                args["config_parser"] = simulator_config
                fmu_description = read_model_description(simulator)
                if fmu_description.fmiVersion == "3.0":
                    # fmu3_client = FMU3Client(
                    #     config_parser=simulator_config,
                    #     config_override=ClientConfigOverride(
                    #         server_host=self._server_args._args.host,
                    #         server_port=self._server_args._args.port,
                    #     ),
                    #     dask_connection=True,
                    # )
                    if simulator_name in self.client_dict.keys():
                        future = dask_client.sync(client_submit, client_function=FMU3Client, args=args)
                        self.client_dict[simulator_name] = future
                        # dd.fire_and_forget(future)
                elif fmu_description.fmiVersion == "2.0":
                    # fmu2_client = FMU2Client(
                    #     config_parser=simulator_config,
                    #     config_override=ClientConfigOverride(
                    #         server_host=self._server_args._args.host,
                    #         server_port=self._server_args._args.port,
                    #     ),
                    #     dask_connection=True,
                    # )
                    if simulator_name in self.client_dict.keys():
                        future = dask_client.sync(client_submit, client_function=FMU2Client, args=args)
                        self.client_dict[simulator_name] = future
                        # while future.status != "running" and str(simulator)[-7:]=="794.fmu":
                        #     print(future.status)
                        # dd.fire_and_forget(future)

                else:
                    ClientManager.logger.error(f"Unable to load {simulator}. FMU V1 format not supported.")

            for simulator in simulator_path.glob("*.m"):
                simulator_config = ConfigParser([ini for ini in simulator.parent.glob("*.ini")][0])
                simulator_name = SimulatorConfig.of_config_parser(simulator_config).model_name
                args["config_parser"] = simulator_config

                # matlab_client = MatlabClient(
                #     config_parser=simulator_config,
                #     config_overrides=ClientConfigOverride(
                #         server_host=self._server_args._args.host,
                #         server_port=self._server_args._args.port,
                #     ),
                #     dask_connection=True,
                # )
                if simulator_name in self.client_dict.keys():
                    future = dask_client.sync(client_submit, client_function=MatlabClient, args=args)
                    self.client_dict[simulator_name] = future
                    # dd.fire_and_forget(future)

            for simulator in simulator_path.glob("*.py"):
                simulator_config = ConfigParser([ini for ini in simulator.parent.glob("*.ini")][0])
                simulator_name = SimulatorConfig.of_config_parser(simulator_config).model_name
                args["config_parser"] = simulator_config
                workers = dask_client_ip  # Ensures Pyro client runs on same node as localhost

                # pyro_client = PyroClient(
                #     config_parser=simulator_config,
                #     config_override=ClientConfigOverride(
                #         server_host=self._server_args._args.host,
                #         server_port=self._server_args._args.port,
                #     ),
                #     dask_connection=True,
                # )
                if simulator_name in self.client_dict.keys():
                    future = dask_client.sync(client_submit, client_function=PyroClient, args=args, workers=workers)
                    self.client_dict[simulator_name] = future
                    # dd.fire_and_forget(future)

    @override
    def on_app_shutdown(self) -> None:
        dask_client = dd.get_client()
        dask_client.close()
        # dask_client.shutdown()


async def client_submit(
        client_function: Callable[[ConfigParser, ClientConfigOverride, bool], Client],
        args: dict[str, Any],
        workers: str | None = None,
) -> None:
    dask_client = dd.get_client()
    if workers:
        client_future = dask_client.submit(client_run, client_function, args, workers=workers)
    else:
        client_future = dask_client.submit(client_run, client_function, args)
    dd.fire_and_forget(client_future)


def client_run(
        client_function: Callable[[ConfigParser, ClientConfigOverride, bool], Client],
        args: dict[str, Any],
) -> None:
    dd.get_client()

    simulator_client = client_function(args["config_parser"], args["config_override"], args["dask_connection"])
    simulator_client.start()
    dd.secede()
    simulator_client.wait_until_finished()
