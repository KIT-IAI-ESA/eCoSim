from __future__ import annotations

import threading
from typing import List, Tuple, Callable

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.SimulationStepRequest import SimulationStepRequest
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_state import ClientStates
from ecosim_server.message_buffer import ClientMessageBuffer, BufferedClientMessage


class ClientCommunication:
    _logger = ESPLogger("ClientCommunication")

    def __init__(self,
                 client_states: ClientStates,
                 client_message_buffer: ClientMessageBuffer,
                 ):
        self._client_states = client_states
        self._client_message_buffer = client_message_buffer

    def broadcast(self,
                  message: ESPChannelMessage,
                  ):
        for client_state in self._client_states.client_states.values():
            client_state.connection.send(message)

    def on_messages(self,
                    client_ids: Tuple[ClientID, ...],
                    message_types: Tuple[MessageType, ...],
                    callback: Callable[[BufferedClientMessage], None],
                    ):
        self._client_message_buffer.on_message(client_ids, message_types, callback)

    def remove_on_message_callback(self,
                                   client_ids: Tuple[ClientID, ...],
                                   message_types: Tuple[MessageType, ...],
                                   ):
        self._client_message_buffer.remove_on_message_callback(client_ids, message_types)

    def messages_of(self,
                    client_ids: Tuple[ClientID, ...],
                    message_types: Tuple[MessageType, ...],
                    ) -> List[BufferedClientMessage]:
        return self._client_message_buffer.get_and_delete_of(client_ids=client_ids, message_types=message_types)

    def send_simulation_step(self,
                             current_step: int,
                             client_id: ClientID,
                             values: List[ProtocolInterfaceValue],
                             ):
        def thread_task():
            self._client_states.client_states[client_id].connection.send(
                ESPChannelMessageJson.create(
                    type=MessageType.SIMULATION_STEP,
                    correlation_id=CorrelationId.of_int(current_step),
                    payload=SimulationStepRequest(
                        step=current_step,
                        inputs=values,
                    ),
                )
            )

        thread = threading.Thread(target=thread_task)
        thread.start()
