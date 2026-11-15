from pathlib import Path

from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfig, AppConfigParameter


class CLIArguments(AppConfig):
    def __init__(
        self,
        additional_parameters: list[AppConfigParameter] | None = None,
    ) -> None:
        super().__init__(
            cli_description="This is a client of eCoSim.",
            parameters=[
                AppConfigParameter(
                    name="config-file",
                    required=True,
                    help_text="The path to the config file. This must be relative to the call path or it can be an absolute path.",
                ),
                AppConfigParameter(
                    name="debug",
                    is_flag=True,
                    help_text="enabling debug mode (more logs)",
                ),
                AppConfigParameter(
                    name="server-host",
                    help_text="Override the server host.",
                ),
                AppConfigParameter(
                    name="server-port",
                    transform=lambda x: int(x),
                    help_text="Override the port of the server.",
                ),
                AppConfigParameter(
                    name="image-renderer-port",
                    required=False,
                    default_value=None,
                    transform=lambda x: int(x),
                    help_text="The port for the image renderer socket on the target server. If not set no connection will be opened.",
                ),
                AppConfigParameter(
                    name="communication-protocol",
                    required=False,
                    default_value=None,  # NOTE: the actual default value is specified in ClientConfig
                    help_text=f"The communication protocol to use between client and server. Default: {CommunicationProtocol.TCP_SOCKET}. "
                    + f"Possible: {[p.name for p in CommunicationProtocol]}",
                ),
            ]
            + (additional_parameters or []),
        )

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
