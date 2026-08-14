from __future__ import annotations

import time
from typing import List, Tuple

from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.message_subscription import MessageSubscription
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.message_buffer import BufferedClientMessage
from ecosim_server.server_state import ServerState
from ecosim_server.simulation.current_step_data import CurrentStepData
from ecosim_server.simulation.interface_value_history import InterfaceValueHistory, RestoreData
from ecosim_server.simulation.rendering.rendering_socket import RenderingSocket


class SimulationExecutor:
    logger = ESPLogger("SimulationExecutor")

    _STEP_RESPONSE_TIMEOUT_IN_SECONDS = 30
    _START_RESPONSE_TIMEOUT_IN_SECONDS = 5
    _STOP_RESPONSE_TIMEOUT_IN_SECONDS = 1
    _RESTORE_RESPONSE_TIMEOUT_IN_SECONDS = 60 * 60

    def __init__(
        self,
        simulation_config: SimulationConfig,
        server_config: ServerConfig,
        server_state: ServerState,
        repositories: Repositories,
        server_measurement: ServerTimeMeasurement,
        client_communication: ClientCommunication,
    ):
        self.simulation_config = simulation_config
        self._server_config = server_config
        self._server_state = server_state
        self._current_step: int = 0
        self._value_history = InterfaceValueHistory.for_config(
            repositories=repositories,
            server_config=server_config,
            simulation_config=simulation_config,
        )
        self._client_communication: ClientCommunication = client_communication
        self._current_step_data = CurrentStepData(
            server_config=server_config,
            simulation_config=simulation_config,
        )
        self._server_measurement = server_measurement
        self._pace_sleep = 4 - (4 * simulation_config.pace)
        if self._pace_sleep != 0:
            SimulationExecutor.logger.info(
                "The execution has set up a pace throttle. Between each execution step the thread is paused for %ss.",
                self._pace_sleep,
            )
        else:
            SimulationExecutor.logger.debug("No execution pace throttle is set.")
        self._rendering_socket: RenderingSocket | None = None
        self._rendering_interval: int | None = self._server_config.server.image_renderer_interval
        self._step_message_client_ids: Tuple[ClientID, ...] = simulation_config.client_ids()

    def execute(
        self,
        rendering_socket: RenderingSocket | None,
    ) -> None:
        self._rendering_socket = rendering_socket
        if not self._server_state.are_all_clients_connected_and_ready():
            raise RuntimeError(
                "Tried to start simulation executor but not all clients are connected and ready",
            )
        if self.simulation_config.restore:
            self._server_measurement.set_start(
                ServerTimeMeasurementType.RESTORE_SIMULATION_RUN,
            )
            self._restore_simulation_run()
            self._server_measurement.set_end(
                ServerTimeMeasurementType.RESTORE_SIMULATION_RUN,
            )
        else:
            self._server_measurement.set_start(
                ServerTimeMeasurementType.SIMULATION_START,
            )
            self._start_simulation_of_all_clients()
            self._server_measurement.set_end(ServerTimeMeasurementType.SIMULATION_START)
        self._server_measurement.set_start(
            ServerTimeMeasurementType.SIMULATION_EXECUTION,
        )
        self._execute_steps()
        self._server_measurement.set_end(ServerTimeMeasurementType.SIMULATION_EXECUTION)
        self._stop_simulation()

    def _stop_simulation(self) -> None:
        self._server_measurement.set_start(ServerTimeMeasurementType.SIMULATION_STOP)
        SimulationExecutor.logger.info("Sending 'stop simulation' signal to all clients")
        self._server_state.set_is_finished(True)
        self._handle_image_renderer(wait_for_finish_timeout=9)
        self._server_measurement.set_end(ServerTimeMeasurementType.SIMULATION_STOP)

        with self._subscribe_to(MessageType.SIMULATION_STOP) as subscription:
            self._client_communication.broadcast(ESPChannelMessageJson.empty(type=MessageType.SIMULATION_STOP))
            self._wait_for_all_clients_stopped(subscription)
        SimulationExecutor.logger.info("All clients stopped (or are not connected anymore)")

    def _wait_for_all_clients_stopped(
        self,
        subscription: MessageSubscription,
    ) -> None:
        while not self._server_state.have_all_clients_stopped_simulation():
            message = subscription.next_message(timeout_in_seconds=SimulationExecutor._STOP_RESPONSE_TIMEOUT_IN_SECONDS)
            if message is None:
                # on timeout the message is None -> we need to check the client connections
                self._client_communication.check_client_connection_states(
                    attempts=3,
                    time_between_attempts_in_seconds=0.1,
                )
                continue
            self._server_state.client_states.simulation_stopped(client_id=message.client_id)

    def _start_simulation_of_all_clients(
        self,
        store_default_values_in_history: bool = True,
    ) -> None:
        SimulationExecutor.logger.info(
            "Starting simulation on all clients and wait for successful start",
        )
        with self._subscribe_to(MessageType.SIMULATION_START) as subscription:
            self._client_communication.broadcast(ESPChannelMessageJson.empty(type=MessageType.SIMULATION_START))
            self._wait_for_all_clients_started(subscription, store_default_values_in_history)
        SimulationExecutor.logger.debug(
            "Starting of simulations of all clients successful",
        )

    def _wait_for_all_clients_started(
        self,
        subscription: MessageSubscription,
        store_default_values_in_history: bool,
    ) -> None:
        while not self._server_state.have_all_clients_started_simulation():
            if not self._server_state.are_all_clients_connected_and_ready():
                raise RuntimeError("A client was lost while waiting for all clients to start their simulation")
            message = subscription.next_message(
                timeout_in_seconds=SimulationExecutor._START_RESPONSE_TIMEOUT_IN_SECONDS,
            )
            if message is None:
                SimulationExecutor.logger.info("Still waiting for all clients to start their simulation")
                continue
            self._handle_simulation_started(message, store_default_values_in_history)

    def _handle_simulation_started(
        self,
        message: BufferedClientMessage,
        store_default_values_in_history: bool,
    ) -> None:
        self._server_state.client_states.simulation_started(client_id=message.client_id)
        if not store_default_values_in_history:
            return
        self._value_history.add_default_values(
            client_id=message.client_id,
            client_sim_step_data=message.payload(ClientSimStepData),
        )

    def _subscribe_to(
        self,
        message_type: MessageType,
    ) -> MessageSubscription:
        return self._client_communication.subscribe(
            client_ids=self._server_state.client_states.all_client_ids(),
            message_types=(message_type,),
        )

    def _restore_simulation_run(self) -> None:
        SimulationExecutor.logger.info("[Restore simulation] Starting restore for all clients and waiting for successful start.")
        self._value_history.init_from_repositories()
        restore_data = self._value_history.calculate_current_execution_step_or_exception()
        self._current_step = restore_data.current_step
        SimulationExecutor.logger.debug("[Restore simulation] the latest completed step is: %s -> restoring until this step.", self._current_step)
        save_defaults = False
        if not self._value_history.contains_all_default_values():
            SimulationExecutor.logger.debug("[Restore simulation] no (or not all default) values are stored in the history: saving them now")
            save_defaults = True
        self._start_simulation_of_all_clients(store_default_values_in_history=save_defaults)
        SimulationExecutor.logger.debug("[Restore simulation] sending step batch to clients")

        # In theory, you can slice the batch data into different chunks. E.g. to keep the transferred data smaller.
        # To do this, you need to slice the batch and set for each batch its own start_date.
        # The start_date is used to correlate the responses from the clients.
        # Then you can wait after each chunk for its response and then, you can send the next chunk.

        with self._subscribe_to(MessageType.SIMULATION_STEP_BATCH) as subscription:
            handled_client_ids = self._send_restore_batches(restore_data)
            if len(handled_client_ids) > 0:
                SimulationExecutor.logger.debug("[Restore simulation] waiting for step batch responses")
                self._current_step_data.reset_for_new_step(step=self._current_step)
                self._wait_for_restore_responses(subscription, handled_client_ids)
        SimulationExecutor.logger.info(
            "[Restore simulation] Restoring simulation on all clients successful - continuing from step %s.",
            self._current_step,
        )

    def _send_restore_batches(
        self,
        restore_data: RestoreData,
    ) -> Tuple[ClientID, ...]:
        """Sends the restore batch to every client that has data to restore and returns exactly those clients."""
        handled_client_ids: List[ClientID] = []
        for client_id in self._server_state.client_states.all_client_ids():
            data_for_restoration = restore_data.client_restore_data[client_id]
            if not data_for_restoration or len(data_for_restoration) == 0:
                SimulationExecutor.logger.debug("[Restore simulation] sending step batch to clients: client %s has no data to restore.", client_id)
                continue
            handled_client_ids.append(client_id)
            self._client_communication.send_simulation_step_batch(
                client_id=client_id,
                data=SimulationStepBatchRequest(
                    start_datetime=self.simulation_config.start_date,
                    inputs=data_for_restoration,
                ),
            )
        return tuple(handled_client_ids)

    def _wait_for_restore_responses(
        self,
        subscription: MessageSubscription,
        client_ids: Tuple[ClientID, ...],
    ) -> None:
        missing_client_ids = set(client_ids)
        while len(missing_client_ids) > 0:
            message = subscription.next_message(timeout_in_seconds=SimulationExecutor._RESTORE_RESPONSE_TIMEOUT_IN_SECONDS)
            if message is None:
                raise RuntimeError(f"Timeout while waiting for the restore response of the clients {missing_client_ids}")
            if self._is_expected_restore_response(message):
                missing_client_ids.discard(message.client_id)

    def _is_expected_restore_response(
        self,
        message: BufferedClientMessage,
    ) -> bool:
        expected_correlation_id = CorrelationId.of_date_time(self.simulation_config.start_date)
        if message.message.correlation_id() == expected_correlation_id:
            return True
        SimulationExecutor.logger.error(
            "Received a %s message from client %s with a wrong correlation_id. Expected response for start date %s but got %s",
            MessageType.SIMULATION_STEP_BATCH,
            message.client_id,
            self.simulation_config.start_date,
            message.message.correlation_id(),
        )
        return False

    def _execute_steps(self) -> None:
        self.logger.debug("Executing steps")
        with self._client_communication.subscribe(
            client_ids=self._step_message_client_ids,
            message_types=(MessageType.SIMULATION_STEP,),
        ) as subscription:
            while self._current_step < self.simulation_config.steps:
                self.logger.info("Step %s: Executing step", self._current_step)
                self._current_step_data.reset_for_new_step(step=self._current_step)
                self._execute_logical_delays()
                self._execute_step(subscription)
                self._handle_image_renderer()
                self._current_step += 1

    def _execute_step(
        self,
        subscription: MessageSubscription,
    ) -> None:
        while not self._current_step_data.all_clients_executed():
            if not self._execute_possible_parts("Periodic possible parts execution", subscription):
                raise RuntimeError(
                    f"Step {self._current_step}: no client is ready for execution but the step is not complete. "
                    + "This means the clients wait for each other - check the interface connections for a cycle.",
                )

    def _execute_logical_delays(self) -> None:
        self.logger.debug("Step %s: Execute logical delays", self._current_step)
        delays_by_delay_step = self._current_step_data.logical_delays_by_delay_step().get_snapshot()
        for delayed_time_steps in sorted(delays_by_delay_step.keys()):
            self.logger.info("Step %s: Execute logical delays at '%s'", self._current_step, delayed_time_steps)
            for logical_delay_connection in delays_by_delay_step[delayed_time_steps].connections:
                self.logger.debug(
                    "Step %s: Execute logical delay '%s': %s -> %s",
                    self._current_step,
                    delayed_time_steps,
                    logical_delay_connection.output_interface,
                    logical_delay_connection.current_value,
                )
                self._current_step_data.set_value(
                    logical_delay_connection.output_interface,
                    logical_delay_connection.current_value,
                )

    def _execute_possible_parts(
        self,
        part_description: str,
        subscription: MessageSubscription,
    ) -> bool:
        """Executes every client whose inputs are complete. Returns False if no client was ready, so no progress was made."""
        ready_for_execution_data_by_clients: dict[
            ClientID,
            List[ProtocolInterfaceValue],
        ] = self._current_step_data.get_ready_for_execution()
        if len(ready_for_execution_data_by_clients) == 0:
            self.logger.debug("Step %s: Executing possible parts: %s: Nothing to do.", self._current_step, part_description)
            return False
        if self.logger.is_debug_enabled:
            self.logger.debug(
                "Step %s: Execute possible parts: %s - %s clients are ready: %s",
                self._current_step,
                part_description,
                len(ready_for_execution_data_by_clients),
                ", ".join(str(client_id) for client_id in ready_for_execution_data_by_clients.keys()),
            )
        for client_id in ready_for_execution_data_by_clients:
            self.logger.debug("Step %s: Execute possible parts: %s - execute client %s", self._current_step, part_description, client_id)
            self._pace_throttle()
            self._client_communication.send_simulation_step(
                current_step=self._current_step,
                client_id=client_id,
                values=ready_for_execution_data_by_clients[client_id],
            )
        handled_clients: dict[ClientID, bool] = {client_id: False for client_id in ready_for_execution_data_by_clients}

        self.logger.debug("Step %s: Waiting for results after executing possible parts: %s", self._current_step, part_description)

        while not all(handled_clients.values()):
            received_message = subscription.next_message(
                timeout_in_seconds=SimulationExecutor._STEP_RESPONSE_TIMEOUT_IN_SECONDS,
            )
            if received_message is None:
                self.logger.warning(
                    "Step %s: still waiting for a response from %s",
                    self._current_step,
                    ", ".join(str(client_id) for client_id, handled in handled_clients.items() if not handled),
                )
                continue
            self._handle_received_sim_step(
                received_message=received_message,
                ready_for_execution_data_by_clients=ready_for_execution_data_by_clients,
                handled_clients=handled_clients,
            )

        for client in handled_clients:
            self._current_step_data.set_is_executed(client)

        self.logger.debug("Finished executing possible parts: %s", part_description)
        return True

    def _handle_received_sim_step(
        self,
        received_message: BufferedClientMessage,
        ready_for_execution_data_by_clients: dict[ClientID, List[ProtocolInterfaceValue]],
        handled_clients: dict[ClientID, bool],
    ) -> bool:
        """Returns False if the message did not belong to the clients this round is waiting for."""
        client_id = received_message.client_id
        if received_message.message.correlation_id().to_int() != self._current_step:
            SimulationExecutor.logger.error(
                "Received a %s message from client %s with a wrong correlation_id. Expected %s but got %s",
                MessageType.SIMULATION_STEP,
                client_id,
                self._current_step,
                received_message.message.correlation_id(),
            )
            return False
        sim_step_data: ClientSimStepData = received_message.payload(
            ClientSimStepData,
        )
        SimulationExecutor.logger.debug(
            "Processing a message containing a simulation step from client %s on step %s: %s",
            client_id,
            self._current_step,
            sim_step_data,
        )
        interface_values = tuple(sim_step_data.interface_values)
        self._value_history.add(
            time_step=self._current_step,
            client_id=client_id,
            interface_values=interface_values + tuple(ready_for_execution_data_by_clients[client_id]),
        )
        self._current_step_data.add_received_data(client_id, interface_values)
        SimulationExecutor.logger.debug(
            "Processing a message containing a simulation step from client %s on step %s: %s: DONE",
            client_id,
            self._current_step,
            sim_step_data,
        )
        handled_clients[client_id] = True
        return True

    def _pace_throttle(self) -> None:
        if self._pace_sleep == 0:
            return
        time.sleep(self._pace_sleep)

    def _handle_image_renderer(
        self,
        wait_for_finish_timeout: int | None = None,
    ) -> None:
        if not self._rendering_socket:
            return
        if not self._rendering_interval:
            return
        step = self._current_step
        # NOTE: step counts start from zero (so for modulo we need to add 1)
        if step != 0 and (step + 1) % self._rendering_interval != 0 or step >= self.simulation_config.steps:
            return
        SimulationExecutor.logger.debug("Rendering images at %s", step)
        end_event = self._rendering_socket.request_and_send_images(step)
        if wait_for_finish_timeout is not None:
            end_event.wait(wait_for_finish_timeout)

    def force_stop(self) -> None:
        if self._server_state.is_running():
            SimulationExecutor.logger.debug("Executing force shutdown")
            self._server_state.force_stop()
