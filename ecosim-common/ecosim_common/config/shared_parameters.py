from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.config_parser import ConfigParser

SERVER_CONNECTION = "server connection"

DEBUG_PARAMETER = AppConfigParameter(
    name="debug",
    is_flag=True,
    help_text="Show debug messages and the full traceback of an error.",
)

COMMUNICATION_PROTOCOL_PARAMETER = AppConfigParameter(
    name="communication-protocol",
    group=SERVER_CONNECTION,
    transform=ConfigParser.choice_name,
    choices=tuple(protocol.serialized for protocol in CommunicationProtocol),
    help_text=f"The protocol between the server and the clients, by default {CommunicationProtocol.TCP_SOCKET.serialized}. "
    + "Overrides communication_protocol in the [server] section of the config file.",
)
