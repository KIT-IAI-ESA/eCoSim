import sys
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_server.config.cli_arguments import CLIArguments


def _parse_positive_thread_count(value: str) -> int:
    threads_per_worker = int(value)
    if threads_per_worker < 1:
        raise ValueError(f"--threads-per-worker must be at least 1, not {value}.")
    return threads_per_worker


class HPCServerCliArguments(CLIArguments):
    DEFAULT_SCHEDULER_FILE: str = "scheduler.json"

    def __init__(
        self,
        ignore_unknown_arguments: bool = False,
    ) -> None:
        args = sys.argv[1:]
        args.append("--communication-protocol")
        args.append(CommunicationProtocol.DASK.name)
        super().__init__(
            passed_arguments=args,
            ignore_unknown_arguments=ignore_unknown_arguments,
            additional_parameters=[
                AppConfigParameter(
                    name="simulator-dir",
                    required=True,
                    help_text="The path to the directory containing all simulators. This must be a relative to the call path or it can be an"
                    + " absolute path.",
                ),
                AppConfigParameter(
                    name="interactive",
                    is_flag=True,
                    help_text="Connects to a running Dask scheduler through its scheduler file. If not set, the simulation runs in batch mode: "
                    + "started through mpirun, with the Dask cluster and the simulation in one MPI job.",
                ),
                AppConfigParameter(
                    name="scheduler-file",
                    default_value=self.DEFAULT_SCHEDULER_FILE,
                    help_text="Interactive mode only: the path to the file the Dask scheduler wrote. This must be relative to the call path or it "
                    + "can be an absolute path.",
                ),
                AppConfigParameter(
                    name="network-interface",
                    help_text="Batch mode only: the network interface of the Dask scheduler and workers, like enp3s0, eno1, eth0 or ib0. "
                    + "If not set, dask_mpi chooses.",
                ),
                AppConfigParameter(
                    name="threads-per-worker",
                    transform=_parse_positive_thread_count,
                    help_text="Batch mode only: the number of threads of each Dask worker. If not set, dask_mpi chooses.",
                ),
            ],
        )

    def interactive(self) -> bool:
        return self._args.interactive

    def simulator_dir(self) -> str:
        return self._args.simulator_dir

    def scheduler_file(self) -> Path:
        return Path.cwd() / self._args.scheduler_file

    def network_interface(self) -> str | None:
        return self._args.network_interface

    def threads_per_worker(self) -> int | None:
        return self._args.threads_per_worker
