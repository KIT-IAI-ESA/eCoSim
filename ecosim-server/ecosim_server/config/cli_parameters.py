"""The options of ecosim-server in their help sections, without the database. ecosim-hpc and the ecosim command reuse them."""

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.option_values import number_from_zero_to_one, port_number, positive_whole_number
from ecosim_common.config.shared_parameters import SERVER_CONNECTION

CONFIG_FILES = "config files"
RUN = "run"
IMAGE_RENDERING = "image rendering"

CONFIG_FILE_PARAMETERS = (
    AppConfigParameter(
        name="server-config",
        group=CONFIG_FILES,
        required=True,
        metavar="FILE",
        help_text="The server's config file, usually server/preferences.ini. A relative path starts in the current folder.",
    ),
    AppConfigParameter(
        name="simulation-config",
        group=CONFIG_FILES,
        required=True,
        metavar="FILE",
        help_text="The simulators and their connections, usually server/simulation.json. A relative path starts in the current folder.",
    ),
)

RUN_PARAMETERS = (
    AppConfigParameter(
        name="steps",
        group=RUN,
        required=True,
        transform=positive_whole_number,
        metavar="N",
        help_text="How many steps the simulation runs. With --restore-simulation-run, the steps of the whole run.",
    ),
    AppConfigParameter(
        name="step-size",
        group=RUN,
        transform=positive_whole_number,
        metavar="MILLISECONDS",
        help_text="The simulated time of one step. Overrides setup.delta_t in the simulation config.",
    ),
    AppConfigParameter(
        name="pace",
        group=RUN,
        default_value="1",
        transform=number_from_zero_to_one,
        metavar="NUMBER",
        help_text="Slows the run down: before the server sends a simulator its step, it waits 0 seconds at 1, 2 seconds at 0.5 and 4 seconds at 0.",
    ),
    AppConfigParameter(
        name="restore-simulation-run",
        group=RUN,
        is_flag=True,
        help_text="Continues an aborted run from its stored results, or starts a new run if there is none. "
        + "The config files must not have changed: the stored results are mapped to steps with the current step size and start date.",
    ),
)

SERVER_ADDRESS_PARAMETERS = (
    AppConfigParameter(
        name="host",
        group=SERVER_CONNECTION,
        metavar="HOST",
        help_text="The host name or IP address the server listens on. Overrides host in the [server] section of the config file.",
    ),
    AppConfigParameter(
        name="port",
        group=SERVER_CONNECTION,
        transform=port_number,
        metavar="PORT",
        help_text="The port the server listens on. Overrides port in the [server] section of the config file.",
    ),
)

IMAGE_RENDERING_PARAMETERS = (
    AppConfigParameter(
        name="image-renderer-port",
        group=IMAGE_RENDERING,
        transform=port_number,
        metavar="PORT",
        help_text="The port of the image rendering socket. Without it, the server opens no such socket.",
    ),
    AppConfigParameter(
        name="image-renderer-interval",
        group=IMAGE_RENDERING,
        transform=positive_whole_number,
        metavar="N",
        help_text="Renders images every N steps and sends them over the image rendering socket. Without it, no images are sent.",
    ),
)
