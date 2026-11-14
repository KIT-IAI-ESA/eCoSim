from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.option_values import choice_name

SERVER_CONNECTION = "server connection"

DEBUG_PARAMETER = AppConfigParameter(
    name="debug",
    is_flag=True,
    help_text="More log messages, to find a problem.",
)

COMMUNICATION_PROTOCOL_PARAMETER = AppConfigParameter(
    name="communication-protocol",
    group=SERVER_CONNECTION,
    transform=choice_name,
    choices=tuple(protocol.serialized for protocol in CommunicationProtocol),
    help_text="How the server and the clients talk to each other. Overrides communication_protocol in the [server] section of the "
    + f"config file. If neither sets it, {CommunicationProtocol.TCP_SOCKET.serialized}.",
)
