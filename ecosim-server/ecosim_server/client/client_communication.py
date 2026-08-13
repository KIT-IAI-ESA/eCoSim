from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, ClassVar, List, Tuple

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_server.client.client_states import ClientStates
from ecosim_server.message_buffer import BufferedClientMessage, ClientMessageBuffer


@dataclass
class ClientCommunication:
    _logger: ClassVar[ESPLogger] = ESPLogger("ClientCommunication")

    _client_states: ClientStates = field()
    _client_message_buffer: ClientMessageBuffer = field()
    _communication_protocol: CommunicationProtocol = field()

    def broadcast(
        self,
        message: ESPChannelMessage,
    ) -> None:
        for client_state in self._client_states.all_states():
            if not client_state.connection:
                ClientCommunication._logger.warning("Cannot broadcast to %s because connection is not set.", client_state.client_id)
                continue
            client_state.connection.send(message)

    def on_messages(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
        callback: Callable[[BufferedClientMessage], None],
    ) -> ClientCommunicationCallbackHandler:
        self._client_message_buffer.on_message(client_ids, message_types, callback)
        return ClientCommunicationCallbackHandler(client_ids, message_types, self._client_message_buffer)

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
            connection = self._client_states.get_connection_for(client_id)
            if connection is None:
                ClientCommunication._logger.warning("Cannot send simulation step to %s because connection is not set.", client_id)
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
            connection = self._client_states.get_connection_for(client_id)
            if connection is None:
                ClientCommunication._logger.warning("Cannot send simulation step to %s because connection is not set.", client_id)
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

    def check_client_connection_states(
        self,
        attempts: int = 5,
        time_between_attempts_in_seconds: float = 1.3,
    ) -> None:
        """
        This method will check the connection states of all clients. It mainly uses PING to check if the connection is still alive. If the ping
        fails too often, the connection will be declared as 'connected=false'.
        """
        ClientCommunication._logger.debug("Checking client connection states...")
        for client_state in self._client_states.all_states():
            if not client_state.connection:
                continue

            ping_message = ESPChannelMessageJson.empty(MessageType.PING)
            for attempt in range(attempts):
                try:
                    event = ParallelEvent.for_communication_protocol(self._communication_protocol)
                    callback_handler = self.on_messages(
                        client_ids=(client_state.client_id,),
                        message_types=(MessageType.PING,),
                        callback=lambda m: event.set(),
                    )
                    client_state.connection.send(ping_message)
                    success = event.wait(timeout=time_between_attempts_in_seconds)
                    callback_handler.remove_callback()
                    if not success:
                        raise TimeoutError(f"timeout for {client_state.client_id}")
                    ClientCommunication._logger.debug("Checking client connection states: reached %s", client_state.client_id)
                    if not client_state.connected:
                        self._client_states.set_client_connected_state(client_state.client_id, True)
                    break
                except Exception as e:
                    if attempt < (attempts - 1):
                        ClientCommunication._logger.debug(
                            "Checking client connection states: exception contacting %s: %s -> retry %s",
                            client_state.client_id,
                            e,
                            attempt,
                        )
                        continue
                    ClientCommunication._logger.debug(
                        "Checking client connection states: exception contacting %s: %s -> reached end of retries",
                        client_state.client_id,
                        e,
                    )
                    if client_state.connected:
                        self._client_states.set_client_connected_state(client_state.client_id, False)
        ClientCommunication._logger.debug("Checking client connection states...done")


@dataclass
class ClientCommunicationCallbackHandler:
    _client_ids: Tuple[ClientID, ...] = field()
    _message_types: Tuple[MessageType, ...] = field()
    _client_message_buffer: ClientMessageBuffer = field()

    def remove_callback(self) -> None:
        self._client_message_buffer.remove_on_message_callback(
            self._client_ids,
            self._message_types,
        )
