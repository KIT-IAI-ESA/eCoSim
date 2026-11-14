from pathlib import Path
from typing import Sequence, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.config.option_values import positive_whole_number
from ecosim_common.config.shared_parameters import COMMUNICATION_PROTOCOL_PARAMETER
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.cli_parameters import CONFIG_FILES

CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-hpc",
    description="Runs the server and every client of a simulation on a Dask cluster, for example in an HPC job. "
    + "Each folder in --simulator-dir is one simulator. The server and the clients always talk over Dask. "
    + "Started with mpirun, it starts its own Dask cluster: rank 0 is the scheduler, rank 1 the server, every other rank a worker. "
    + "With --interactive it uses a running Dask scheduler instead.",
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
        # the protocol is always Dask, see communication_protocol()
        server_parameters = [parameter for parameter in super().parameters() if parameter is not COMMUNICATION_PROTOCOL_PARAMETER]
        return [
            *server_parameters,
            AppConfigParameter(
                name="simulator-dir",
                group=CONFIG_FILES,
                required=True,
                metavar="FOLDER",
                help_text="The folder with one folder per simulator, usually Modules. The files in a simulator's folder choose its client: "
                + "an FMU client for each .fmu file, the Pyro5 client for .py files, the MATLAB client for .m files.",
            ),
            AppConfigParameter(
                name="interactive",
                group=DASK_CLUSTER,
                is_flag=True,
                help_text="Connects to a running Dask scheduler through its scheduler file, instead of starting a cluster with mpirun.",
            ),
            AppConfigParameter(
                name="scheduler-file",
                group=DASK_CLUSTER,
                default_value=cls.DEFAULT_SCHEDULER_FILE,
                metavar="FILE",
                help_text="With --interactive: the file the Dask scheduler wrote. A relative path starts in the current folder.",
            ),
            AppConfigParameter(
                name="network-interface",
                group=DASK_CLUSTER,
                metavar="NAME",
                help_text="With mpirun: the network interface of the Dask scheduler and the workers, like enp3s0, eno1, eth0 or ib0. "
                + "Without it, dask_mpi chooses.",
            ),
            AppConfigParameter(
                name="threads-per-worker",
                group=DASK_CLUSTER,
                default_value=str(cls.DEFAULT_THREADS_PER_WORKER),
                transform=positive_whole_number,
                metavar="N",
                help_text="With mpirun: the threads of each Dask worker. A job with only one worker needs at least 2.",
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
