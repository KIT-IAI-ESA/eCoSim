from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config.app_config import AppConfigParameter


class FMPyCliArguments(CLIArguments):
    def __init__(
        self,
        additional_parameters: list[AppConfigParameter] | None = None,
    ) -> None:
        super().__init__(
            additional_parameters=(additional_parameters or [])
            + [
                AppConfigParameter(
                    name="validate-fmu-file-only",
                    required=False,
                    is_flag=True,
                    help_text="Only validate the FMU file - no client will be started.",
                ),
            ],
        )
