from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Iterable, List, Tuple

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.client.client_message import ClientMessage
from ecosim_server.client.client_message_buffer import ClientMessageBuffer
from ecosim_server.client.client_state import ClientState
from ecosim_server.client.client_states import ClientStates
from ecosim_server.client.message_subscription import MessageSubscription
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig


@dataclass
class ClientCommunication:
    _logger: ClassVar[ESPLogger] = ESPLogger("ClientCommunication")

    _client_states: ClientStates = field()
    _client_message_buffer: ClientMessageBuffer = field()

    @staticmethod
    def of(
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
    ) -> ClientCommunication:
        return ClientCommunication(
            _client_message_buffer=ClientMessageBuffer.for_communication_protocol(server_config.server.communication_protocol),
            _client_states=ClientStates.for_config(
                server_config=server_config,
                simulation_config=simulation_config,
            ),
        )

    def broadcast(
        self,
        message: ESPChannelMessage,
    ) -> None:
        for client_state in self._client_states.all_states():
            if not client_state.connection:
                ClientCommunication._logger.warning("Cannot broadcast to %s because connection is not set.", client_state.client_id)
                continue
            try:
                client_state.connection.send(message)
            except Exception as error:
                raise RuntimeError(self._send_failure_text(client_id=client_state.client_id, message_type=message.type(), error=error)) from error

    def subscribe(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> MessageSubscription:
        """
        Opens a subscription that queues every matching message until it is closed.

        Use this - not a callback registered and removed around every single wait - whenever a caller waits
        for messages in a loop, see 'MessageSubscription'.
        """
        return MessageSubscription.open(
            message_buffer=self._client_message_buffer,
            client_ids=client_ids,
            message_types=message_types,
        )

    def send_simulation_step(
        self,
        current_step: int,
        client_id: ClientID,
        values: List[ProtocolInterfaceValue],
    ) -> None:
        def send() -> None:
            self._connection_of(client_id).send(
                ESPChannelMessageJson.create(
                    type=MessageType.SIMULATION_STEP,
                    correlation_id=CorrelationId.of_int(current_step),
                    payload=SimulationStepRequest(
                        step=current_step,
                        inputs=values,
                    ),
                ),
            )

        self._send_async(client_id=client_id, message_type=MessageType.SIMULATION_STEP, send=send)

    def send_simulation_step_batch(
        self,
        client_id: ClientID,
        data: SimulationStepBatchRequest,
    ) -> None:
        def send() -> None:
            self._connection_of(client_id).send(
                ESPChannelMessageJson.create(
                    type=MessageType.SIMULATION_STEP_BATCH,
                    correlation_id=CorrelationId.of_date_time(data.start_datetime),
                    payload=data,
                ),
            )

        self._send_async(client_id=client_id, message_type=MessageType.SIMULATION_STEP_BATCH, send=send)

    def _connection_of(self, client_id: ClientID) -> ClientConnection:
        connection = self._client_states.get_connection_for(client_id)
        if connection is None:
            raise ConnectionError("The connection is not set.")
        return connection

    def _send_async(
        self,
        client_id: ClientID,
        message_type: MessageType,
        send: Callable[[], None],
    ) -> None:
        def thread_task() -> None:
            try:
                send()
            except Exception as error:
                self._report_send_failure(client_id=client_id, message_type=message_type, error=error)

        thread = threading.Thread(target=thread_task)
        thread.start()

    def _report_send_failure(
        self,
        client_id: ClientID,
        message_type: MessageType,
        error: Exception,
    ) -> None:
        failure = self._send_failure_text(client_id=client_id, message_type=message_type, error=error)
        ClientCommunication._logger.error("%s", failure)
        # it has the type of the failed message, so it lands in the queue of whoever waits for the answer
        self._client_message_buffer.add_buffered(
            ClientMessage(client_id=client_id, message=ESPChannelMessageJson.empty(type=message_type), send_failure=failure),
        )

    @staticmethod
    def _send_failure_text(
        client_id: ClientID,
        message_type: MessageType,
        error: Exception,
    ) -> str:
        return f"Sending {message_type.name} to client {client_id} failed: {error}"

    def check_client_connection_states(
        self,
        attempts: int = 5,
        time_between_attempts_in_seconds: float = 1.3,
    ) -> None:
        """
        This method will check the connection states of all clients. It mainly uses MessageType.PING to check if the connection is still alive.
        If the ping fails too often, the connection will be declared as 'connected=false'.
        """
        ClientCommunication._logger.debug("Checking client connection states...")
        for client_state in self._client_states.all_states():
            if not client_state.connection:
                continue
            reached = self._is_client_reachable(client_state, attempts, time_between_attempts_in_seconds)
            if reached != client_state.connected:
                self._client_states.set_client_connected_state(client_state.client_id, reached)
        ClientCommunication._logger.debug("Checking client connection states...done")

    def _is_client_reachable(
        self,
        client_state: ClientState,
        attempts: int,
        time_between_attempts_in_seconds: float,
    ) -> bool:
        """Pings the client until it answers. The subscription stays open over all attempts so no answer is missed."""
        with self.subscribe(client_ids=(client_state.client_id,), message_types=(MessageType.PING,)) as subscription:
            for attempt in range(attempts):
                if self._ping_once(client_state, subscription, time_between_attempts_in_seconds):
                    ClientCommunication._logger.debug("Checking client connection states: reached %s", client_state.client_id)
                    return True
                ClientCommunication._logger.debug(
                    "Checking client connection states: no answer from %s -> attempt %s of %s",
                    client_state.client_id,
                    attempt + 1,
                    attempts,
                )
        return False

    @staticmethod
    def _ping_once(
        client_state: ClientState,
        subscription: MessageSubscription,
        timeout_in_seconds: float,
    ) -> bool:
        try:
            if client_state.connection is None:
                return False
            subscription.pending_messages()  # answers to an earlier ping must not count for this one
            client_state.connection.send(ESPChannelMessageJson.empty(MessageType.PING))
            return subscription.next_message(timeout_in_seconds=timeout_in_seconds) is not None
        except Exception as e:
            ClientCommunication._logger.debug("Checking client connection states: exception contacting %s: %s", client_state.client_id, e)
            return False

    def wait_for_all_clients_connected_and_ready(self) -> None:
        self._client_states.wait_for_all_clients_connected_and_ready()

    def add_if_needed(
        self,
        client_config: ClientMetaData,
        connection: ClientConnection,
    ) -> bool:
        return self._client_states.add_if_needed(client_config, connection)

    def interfaces_validated(self, client_id: ClientID) -> None:
        self._client_states.interfaces_validated(client_id)

    def step_size_accepted(self, client_id: ClientID) -> None:
        self._client_states.step_size_accepted(client_id)

    def set_client_ready_for_simulation(self, client_id: ClientID) -> None:
        self._client_states.set_client_ready_for_simulation(client_id)

    def set_client_connected_state(self, client_id: ClientID, connected: bool) -> None:
        self._client_states.set_client_connected_state(client_id, connected)

    def add_message_from_client(self, client_id: ClientID, received_message: ESPChannelMessage) -> None:
        self._client_message_buffer.add(
            client_id=client_id,
            message=received_message,
        )

    def reset_state(self, client_id: ClientID) -> None:
        self._client_states.reset_state(client_id)

    def lost_client_ids(self, client_ids: Iterable[ClientID]) -> Tuple[ClientID, ...]:
        return self._client_states.lost_client_ids(client_ids)

    def are_all_clients_connected_and_ready(self) -> bool:
        return self._client_states.are_all_clients_connected_and_ready()

    def have_all_clients_stopped_simulation(self) -> bool:
        return self._client_states.have_all_clients_stopped_simulation()

    def simulation_stopped(self, client_id: ClientID) -> None:
        self._client_states.simulation_stopped(client_id)

    def have_all_clients_started_simulation(self) -> bool:
        return self._client_states.have_all_clients_started_simulation()

    def simulation_started(self, client_id: ClientID) -> None:
        self._client_states.simulation_started(client_id)

    def all_client_ids(self) -> tuple[ClientID, ...]:
        return self._client_states.all_client_ids()
