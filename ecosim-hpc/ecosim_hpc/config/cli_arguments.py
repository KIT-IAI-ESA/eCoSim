import sys

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_server.config.cli_arguments import CLIArguments


class HPCServerCliArguments(CLIArguments):
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
                    help_text="Establishes interactive version of Dask-MPI. If not set, the simulation will run in batch mode.",
                ),
            ],
        )

    def interactive(self) -> bool:
        return self._args.interactive

    def simulator_dir(self) -> str:
        return self._args.simulator_dir
