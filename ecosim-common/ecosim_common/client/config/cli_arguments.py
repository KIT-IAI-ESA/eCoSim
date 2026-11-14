from pathlib import Path
from typing import Sequence

from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfig, AppConfigParameter
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.config.option_values import port_number
from ecosim_common.config.shared_parameters import COMMUNICATION_PROTOCOL_PARAMETER, DEBUG_PARAMETER, SERVER_CONNECTION


class CLIArguments(AppConfig):
    def __init__(
        self,
        console_script: ConsoleScript,
        passed_arguments: Sequence[str] | None = None,
    ) -> None:
        super().__init__(
            console_script=console_script,
            parameters=self.parameters(),
            passed_arguments=passed_arguments,
        )

    @classmethod
    def parameters(cls) -> list[AppConfigParameter]:
        return [
            AppConfigParameter(
                name="config-file",
                required=True,
                metavar="FILE",
                help_text="The client's config file, usually preferences.ini in the folder of the model. "
                + "A relative path starts in the current folder.",
            ),
            DEBUG_PARAMETER,
            AppConfigParameter(
                name="server-host",
                group=SERVER_CONNECTION,
                metavar="HOST",
                help_text="The host name or IP address of the server. Overrides ip in the [server] section of the config file.",
            ),
            AppConfigParameter(
                name="server-port",
                group=SERVER_CONNECTION,
                transform=port_number,
                metavar="PORT",
                help_text="The port of the server. Overrides port in the [server] section of the config file.",
            ),
            AppConfigParameter(
                name="image-renderer-port",
                group=SERVER_CONNECTION,
                transform=port_number,
                metavar="PORT",
                help_text="The port of the server's image rendering socket. Without it, the client does not connect to it.",
            ),
            COMMUNICATION_PROTOCOL_PARAMETER,
        ]

    def config_file(self) -> Path:
        path: Path = Path(self._args.config_file)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def debug_enabled(self) -> bool:
        return self._args.debug  # type: ignore

    def image_renderer_port(self) -> int | None:
        return self._args.image_renderer_port  # type: ignore

    def communication_protocol(self) -> CommunicationProtocol | None:
        if self._args.communication_protocol is None:
            return None
        return CommunicationProtocol.of(self._args.communication_protocol)

    def config_overrides(self) -> ClientConfigOverride:
        return ClientConfigOverride(
            server_host=self._args.server_host,
            server_port=self._args.server_port,
            image_renderer_port=self._args.image_renderer_port,
            communication_protocol=self.communication_protocol(),
        )

    def get_additional_parameter(self, name: str) -> str | bool | None:
        parameter_name = AppConfigParameter(name=name, help_text="").to_parsed_arg_name()
        return getattr(self._args, parameter_name, None)
