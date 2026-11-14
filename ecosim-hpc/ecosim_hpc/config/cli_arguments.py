from pathlib import Path
from typing import Sequence, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.config.shared_parameters import COMMUNICATION_PROTOCOL_PARAMETER
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.cli_parameters import CONFIG_FILES

CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-hpc",
    description="Runs the server and all clients of a simulation on a Dask cluster. Started with mpirun it starts its own Dask cluster. "
    + "With --interactive it uses a running Dask scheduler.",
    examples=(
        "mpirun -np 4 ecosim-hpc --server-config server/preferences.ini --simulation-config server/simulation.json \\\n"
        + "    --simulator-dir Modules --steps 100 --database-type file",
        "ecosim-hpc --interactive --server-config server/preferences.ini --simulation-config server/simulation.json \\\n"
        + "    --simulator-dir Modules --steps 100 --database-type file",
    ),
)
DASK_CLUSTER = "dask cluster"


class HPCServerCliArguments(CLIArguments):
    DEFAULT_SCHEDULER_FILE: str = "scheduler.json"
    # the accept loop holds one thread for the whole run, so a single worker needs a second one
    DEFAULT_THREADS_PER_WORKER: int = 2

    def __init__(
        self,
        passed_arguments: Sequence[str] | None = None,
    ) -> None:
        super().__init__(passed_arguments=passed_arguments, console_script=CONSOLE_SCRIPT)

    @classmethod
    @override
    def parameters(cls) -> list[AppConfigParameter]:
        # the protocol is always Dask
        server_parameters = [parameter for parameter in super().parameters() if parameter is not COMMUNICATION_PROTOCOL_PARAMETER]
        return [
            *server_parameters,
            AppConfigParameter(
                name="simulator-dir",
                group=CONFIG_FILES,
                required=True,
                metavar="FOLDER",
                help_text="The folder with one folder per simulator, usually Modules. A simulator's folder holds one model, "
                + "which chooses its client: the Python client if the ini file has model in [python], "
                + "else the FMU client for the FMI version of the .fmu file, the MATLAB client for .m files or the Pyro5 client for .py files.",
            ),
            AppConfigParameter(
                name="interactive",
                group=DASK_CLUSTER,
                is_flag=True,
                help_text="Connects to a running Dask scheduler instead of starting a cluster with mpirun.",
            ),
            AppConfigParameter(
                name="scheduler-file",
                group=DASK_CLUSTER,
                default_value=cls.DEFAULT_SCHEDULER_FILE,
                metavar="FILE",
                help_text="The file the Dask scheduler wrote, used with --interactive.",
            ),
            AppConfigParameter(
                name="network-interface",
                group=DASK_CLUSTER,
                metavar="NAME",
                help_text="The network interface of the Dask scheduler and the workers with mpirun, for example ib0.",
            ),
            AppConfigParameter(
                name="threads-per-worker",
                group=DASK_CLUSTER,
                default_value=str(cls.DEFAULT_THREADS_PER_WORKER),
                transform=ConfigParser.positive_whole_number,
                metavar="N",
                help_text="The threads of each Dask worker with mpirun. A job with one worker needs at least 2.",
            ),
        ]

    @override
    def communication_protocol(self) -> CommunicationProtocol:
        return CommunicationProtocol.DASK

    def interactive(self) -> bool:
        return self._args.interactive

    def simulator_dir(self) -> str:
        return self._args.simulator_dir

    def scheduler_file(self) -> Path:
        return Path.cwd() / self._args.scheduler_file

    def network_interface(self) -> str | None:
        return self._args.network_interface

    def threads_per_worker(self) -> int:
        return self._args.threads_per_worker
