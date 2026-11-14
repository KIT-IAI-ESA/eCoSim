from typing import override

from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config.app_config import AppConfigParameter


class FMPyCliArguments(CLIArguments):
    @classmethod
    @override
    def parameters(cls) -> list[AppConfigParameter]:
        return [
            *super().parameters(),
            AppConfigParameter(
                name="validate-fmu-file-only",
                is_flag=True,
                help_text="Only check the FMU, the .fmc file and the [start_values] of the client config. Starts no client.",
            ),
        ]

    def validate_fmu_file_only(self) -> bool:
        return self.get_additional_parameter("validate-fmu-file-only") is True
