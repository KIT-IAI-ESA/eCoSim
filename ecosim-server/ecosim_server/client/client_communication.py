from __future__ import annotations

import threading
from typing import Callable, List, Tuple

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.client.client_states import ClientStates
from ecosim_server.message_buffer import BufferedClientMessage, ClientMessageBuffer


class ClientCommunication:
    _logger = ESPLogger("ClientCommunication")

    def __init__(
        self,
        client_states: ClientStates,
        client_message_buffer: ClientMessageBuffer,
    ):
        self._client_states = client_states
        self._client_message_buffer = client_message_buffer

    def broadcast(
        self,
        message: ESPChannelMessage,
    ) -> None:
        for client_state in self._client_states.client_states.values():
            if not client_state.connection:
                ClientCommunication._logger.warning(f"Cannot broadcast to {client_state.client_id} because connection is not set.")
                continue
            client_state.connection.send(message)

    def on_messages(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
        callback: Callable[[BufferedClientMessage], None],
    ) -> None:
        self._client_message_buffer.on_message(client_ids, message_types, callback)

    # TODO this method is error prone since you must need to remember to call it
    #      refactor it, so 'on_messages' somehow integrates this functionality
    #      e.g. it could return a handle that you can call 'remove' on to remove the callback
    def remove_on_message_callback(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> None:
        self._client_message_buffer.remove_on_message_callback(client_ids, message_types)

    def messages_of(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> List[BufferedClientMessage]:
        return self._client_message_buffer.get_and_delete_of(client_ids=client_ids, message_types=message_types)

    def send_simulation_step(
        self,
        current_step: int,
        client_id: ClientID,
        values: List[ProtocolInterfaceValue],
    ) -> None:
        def thread_task() -> None:
            connection = self._client_states.client_states[client_id].connection
            if connection is None:
                ClientCommunication._logger.warning(f"Cannot send simulation step to {client_id} because connection is not set.")
                return
            connection.send(
                ESPChannelMessageJson.create(
                    type=MessageType.SIMULATION_STEP,
                    correlation_id=CorrelationId.of_int(current_step),
                    payload=SimulationStepRequest(
                        step=current_step,
                        inputs=values,
                    ),
                ),
            )

        thread = threading.Thread(target=thread_task)
        thread.start()

    def send_simulation_step_batch(
        self,
        client_id: ClientID,
        data: SimulationStepBatchRequest,
    ) -> None:
        def thread_task() -> None:
            connection = self._client_states.client_states[client_id].connection
            if connection is None:
                ClientCommunication._logger.warning(f"Cannot send simulation step to {client_id} because connection is not set.")
                return
            connection.send(
                ESPChannelMessageJson.create(
                    type=MessageType.SIMULATION_STEP_BATCH,
                    correlation_id=CorrelationId.of_date_time(data.start_datetime),
                    payload=data,
                ),
            )

        thread = threading.Thread(target=thread_task)
        thread.start()
