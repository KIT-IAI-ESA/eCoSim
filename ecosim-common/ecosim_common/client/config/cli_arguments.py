from pathlib import Path

from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.config.app_config import AppConfig, AppConfigParameter


class CLIArguments(AppConfig):

    def __init__(self) -> None:
        super().__init__(
            cli_description="This is the client of eCoSimPy.",
            parameters=[
                AppConfigParameter(
                    name="config-file",
                    required=True,
                    help_text="The path to the config file. This must be relative to the call path or it can "
                              "be an absolute path.",
                ),
                AppConfigParameter(
                    name="debug",
                    is_flag=True,
                    help_text="enabling debug mode (more logs)",
                ),
                AppConfigParameter(
                    name="simulator-type",
                    default_value="fmu_2",
                    help_text="Specifies the type of simulator in lowercase letters. Default without specification is fmu_2.",
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
            ],
        )

    def config_file(self) -> Path:
        path: Path = Path(self._args.config_file)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def debug_enabled(self) -> bool:
        return self._args.debug  # type: ignore

    def client_type(self) -> str:
        return self._args.simulator_type  # type: ignore

    def image_renderer_port(self) -> int | None:
        return self._args.image_renderer_port  # type: ignore

    def config_overrides(self) -> ClientConfigOverride:
        return ClientConfigOverride(
            server_host=self._args.server_host,
            server_port=self._args.server_port,
            image_renderer_port=self._args.image_renderer_port,
        )
