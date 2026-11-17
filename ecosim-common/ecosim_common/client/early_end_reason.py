from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID


def early_end_reason(last_handled_message_type: MessageType | None, client_id: ClientID) -> str | None:
    match last_handled_message_type:
        case MessageType.CLIENT_META_DATA_REQUEST:
            return (
                f"the server rejected simulator name '{client_id.simulator_name}' and model name '{client_id.model_name}'. "
                + "The simulation config has no simulator with these names or another client already uses them. "
                + "Check simulator_name and model_name in the [simulator] section of the client config."
            )
        case MessageType.INTERFACE_REQUEST:
            return (
                "the server rejected the interfaces of this client. The simulation config marks an interface "
                + "as required that the .fmc file does not list. The server output shows which one."
            )
        case MessageType.SIMULATION_START:
            return "the connection to the server ended at the start of the simulation, before the first step. The server output says why."
        case _:
            return None
