from __future__ import annotations

import sys
import time
from time import sleep
from typing import List, Tuple

from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.message_buffer import BufferedClientMessage
from ecosim_server.server_state import ServerState
from ecosim_server.simulation.current_step_data import CurrentStepData
from ecosim_server.simulation.interface_value_history import InterfaceValueHistory
from ecosim_server.simulation.rendering.rendering_socket import RenderingSocket


# TODO_AFTER_MERGE: we probably need an abstract SimulationExecutor
class SimulationExecutor:
    logger = ESPLogger("SimulationExecutor")

    # How long to wait for a single simulation step response before re-checking whether the run was aborted.
    _STEP_RESPONSE_TIMEOUT_IN_SECONDS = 30

    def __init__(
        self,
        simulation_config: SimulationConfig,
        server_config: ServerConfig,
        server_state: ServerState,
        repositories: Repositories,
        server_measurement: ServerTimeMeasurement,
        global_finish_event: ParallelEvent,
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
        self._client_communication: ClientCommunication = ClientCommunication(
            client_states=server_state.client_states,
            client_message_buffer=server_state.message_buffer,
        )
        self._current_step_data = CurrentStepData(
            server_config=server_config,
            simulation_config=simulation_config,
        )
        self._server_measurement = server_measurement
        self._pace_sleep = 4 - (4 * simulation_config.pace)
        if self._pace_sleep != 0:
            SimulationExecutor.logger.info(
                f"The execution has set up a pace throttle. Between each execution step the thread is paused for {self._pace_sleep}s.",
            )
        else:
            SimulationExecutor.logger.debug("No execution pace throttle is set.")
        self._rendering_socket: RenderingSocket | None = None
        self._rendering_interval: int | None = self._server_config.server.image_renderer_interval
        self._global_finish: ParallelEvent = global_finish_event
        self._step_message_client_ids: Tuple[ClientID, ...] = simulation_config.client_ids()
        self._step_message_queue: ESPQueue[BufferedClientMessage] = ESPQueue[BufferedClientMessage].of_type(
            queue_type=ESPStructureType.DASK_VARIABLE
            if server_config.server.communication_protocol == CommunicationProtocol.DASK
            else ESPStructureType.THREAD,
            dask_name="simulator_message_queue_possible_parts",
        )

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
        self._server_measurement.set_start(ServerTimeMeasurementType.SIMULATION_STOP)
        self._stop_simulation()
        self._server_measurement.set_end(ServerTimeMeasurementType.SIMULATION_STOP)

    def _stop_simulation(self) -> None:
        SimulationExecutor.logger.info("Sending 'stop simulation' signal to all clients")
        self._server_state.set_is_finished(True)
        self._handle_image_renderer(wait_for_finish_timeout=9)

        self._client_communication.broadcast(ESPChannelMessageJson.empty(type=MessageType.SIMULATION_STOP))
        while not self._server_state.have_all_clients_stopped_simulation():
            for message in self._client_communication.messages_of(
                client_ids=self._server_state.client_states.all_client_ids(),
                message_types=(MessageType.SIMULATION_STOP,),
            ):
                self._server_state.client_states.simulation_stopped(
                    client_id=message.client_id,
                )
            # TODO_OSR: refactor to waiting mechanism
            if self._server_config.server.communication_protocol == CommunicationProtocol.TCP_SOCKET:
                sleep(1)
        SimulationExecutor.logger.info("All clients stopped (or are not connected anymore)")

    def _start_simulation_of_all_clients(
        self,
        store_default_values_in_history: bool = True,
    ) -> None:
        SimulationExecutor.logger.info(
            "Starting simulation on all clients and wait for successful start",
        )
        self._client_communication.broadcast(
            ESPChannelMessageJson.empty(type=MessageType.SIMULATION_START),
        )
        while (not self._server_state.have_all_clients_started_simulation()) and self._server_state.are_all_clients_connected_and_ready():
            for message in self._client_communication.messages_of(
                client_ids=self._server_state.client_states.all_client_ids(),
                message_types=(MessageType.SIMULATION_START,),
            ):
                self._server_state.client_states.simulation_started(
                    client_id=message.client_id,
                )
                if store_default_values_in_history:
                    self._value_history.add_default_values(
                        client_id=message.client_id,
                        client_sim_step_data=message.payload(ClientSimStepData),
                    )
            # TODO_AFTER_MERGE: find better solution
            self._abort_if_globally_finished("when starting simulators")
            # TODO_OSR: refactor to waiting mechanism
            if self._server_config.server.communication_protocol == CommunicationProtocol.TCP_SOCKET:
                sleep(1)
        SimulationExecutor.logger.debug(
            "Starting of simulations of all clients successful",
        )

    def _restore_simulation_run(self) -> None:
        SimulationExecutor.logger.info("[Restore simulation] Starting restore for all clients and waiting for successful start.")
        self._value_history.init_from_repositories()
        restore_data = self._value_history.calculate_current_execution_step_or_exception()
        self._current_step = restore_data.current_step
        SimulationExecutor.logger.debug(f"[Restore simulation] the latest completed step is: {self._current_step} -> restoring until this step.")
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

        start_date = self.simulation_config.start_date
        handled_client_ids: List[ClientID] = []

        for client_id in self._server_state.client_states.all_client_ids():
            data_for_restoration = restore_data.client_restore_data[client_id]
            if not data_for_restoration or len(data_for_restoration) == 0:
                SimulationExecutor.logger.debug(f"[Restore simulation] sending step batch to clients: client {client_id} has no data to restore.")
                continue
            handled_client_ids.append(client_id)
            self._client_communication.send_simulation_step_batch(
                client_id=client_id,
                data=SimulationStepBatchRequest(
                    start_datetime=start_date,
                    inputs=data_for_restoration,
                ),
            )

        if len(handled_client_ids) > 0:
            SimulationExecutor.logger.debug("[Restore simulation] waiting for step batch responses")
            self._current_step_data.reset_for_new_step(step=self._current_step)
            responses = {
                client_id: ParallelEvent.for_communication_protocol(
                    communication_protocol=self._server_config.server.communication_protocol,
                    dask_name=client_id.to_str(),
                )
                for client_id in self.simulation_config.client_ids()
            }

            def handle_batch_response(message: BufferedClientMessage) -> None:
                client_id = message.client_id
                if message.message.correlation_id() != CorrelationId.of_date_time(start_date):
                    self.logger.error(
                        f"Received a {MessageType.SIMULATION_STEP_BATCH} message from client {client_id} with a wrong correlation_id. "
                        + f"Expected response for start date {start_date} but got {message.message.correlation_id()}",
                    )
                    return
                responses[client_id].set()

            self._client_communication.on_messages(
                client_ids=tuple(handled_client_ids),
                message_types=(MessageType.SIMULATION_STEP_BATCH,),
                callback=handle_batch_response,
            )

            for client_id, event in responses.items():
                if not event.wait(timeout=60 * 60):
                    raise RuntimeError(f"Timeout while waiting for restore response from client {client_id}")

            self._client_communication.remove_on_message_callback(
                client_ids=self.simulation_config.client_ids(),
                message_types=(MessageType.SIMULATION_STEP_BATCH,),
            )
        SimulationExecutor.logger.info(
            f"[Restore simulation] Restoring simulation on all clients successful - continuing from step {self._current_step}.",
        )

    def _abort_if_globally_finished(
        self,
        context: str,
    ) -> None:
        if self._global_finish is None:
            return
        if not self._global_finish.is_set():
            return
        SimulationExecutor.logger.error(f"Error occurred {context}. Exiting...")
        self.force_stop()
        sys.exit(1)

    def _execute_steps(self) -> None:
        self.logger.debug("Executing steps")
        self._client_communication.on_messages(
            client_ids=self._step_message_client_ids,
            message_types=(MessageType.SIMULATION_STEP,),
            callback=self._step_message_queue.push,
        )
        try:
            while self._current_step < self.simulation_config.steps:
                self.logger.info(f"Step {self._current_step}: Executing step")
                self._current_step_data.reset_for_new_step(step=self._current_step)
                self._execute_logical_delays()

                # TODO: change to a waiting mechanism
                while not self._current_step_data.all_clients_executed():
                    if not self._execute_possible_parts("Periodic possible parts execution"):
                        raise RuntimeError(
                            f"Step {self._current_step}: no client is ready for execution but the step is not complete. "
                            + "This means the clients wait for each other - check the interface connections for a cycle.",
                        )
                    self._abort_if_globally_finished("while running simulators")

                self._handle_image_renderer()
                self._current_step += 1
        finally:
            self._client_communication.remove_on_message_callback(
                self._step_message_client_ids,
                (MessageType.SIMULATION_STEP,),
            )

    def _execute_logical_delays(self) -> None:
        self.logger.debug(f"Step {self._current_step}: Execute logical delays")
        delays_by_delay_step = self._current_step_data.logical_delays_by_delay_step().get_snapshot()
        for delayed_time_steps in sorted(delays_by_delay_step.keys()):
            self.logger.info(f"Step {self._current_step}: Execute logical delays at '{delayed_time_steps}'")
            for logical_delay_connection in delays_by_delay_step[delayed_time_steps].connections:
                self.logger.debug(
                    f"Step {self._current_step}: Execute logical delay '{delayed_time_steps}': "
                    + f"{logical_delay_connection.output_interface} -> {logical_delay_connection.current_value}",
                )
                self._current_step_data.set_value(
                    logical_delay_connection.output_interface,
                    logical_delay_connection.current_value,
                )

    def _execute_possible_parts(
        self,
        part_description: str,
    ) -> bool:
        """Executes every client whose inputs are complete. Returns False if no client was ready, so no progress was made."""
        ready_for_execution_data_by_clients: dict[
            ClientID,
            List[ProtocolInterfaceValue],
        ] = self._current_step_data.get_ready_for_execution()
        if len(ready_for_execution_data_by_clients) == 0:
            self.logger.debug(
                f"Step {self._current_step}: Executing possible parts: {part_description}: Nothing to do.",
            )
            return False
        self.logger.info(
            f"Step {self._current_step}: Execute possible parts: {part_description} - {len(ready_for_execution_data_by_clients)} clients are ready:"
            + f" {', '.join(str(client_id) for client_id in ready_for_execution_data_by_clients.keys())}",
        )
        for client_id in ready_for_execution_data_by_clients:
            self.logger.debug(
                f"Step {self._current_step}: Execute possible parts: {part_description} - execute client {client_id}",
            )
            self._pace_throttle()
            self._client_communication.send_simulation_step(
                current_step=self._current_step,
                client_id=client_id,
                values=ready_for_execution_data_by_clients[client_id],
            )
        handled_clients: dict[ClientID, bool] = {client_id: False for client_id in ready_for_execution_data_by_clients}

        self.logger.debug(
            f"Step {self._current_step}: Waiting for results after executing possible parts: {part_description}",
        )

        while not all(handled_clients.values()):
            received_message = self._step_message_queue.pop_or_none(
                timeout=SimulationExecutor._STEP_RESPONSE_TIMEOUT_IN_SECONDS,
            )
            if received_message is None:
                self._abort_if_globally_finished("while waiting for a simulation step response")
                self.logger.warning(
                    f"Step {self._current_step}: still waiting for a response from "
                    + f"{', '.join(str(client_id) for client_id, handled in handled_clients.items() if not handled)}",
                )
                continue
            self._handle_received_sim_step(
                received_message=received_message,
                ready_for_execution_data_by_clients=ready_for_execution_data_by_clients,
                handled_clients=handled_clients,
            )

        for client in handled_clients:
            self._current_step_data.set_is_executed(client)

        self.logger.debug(f"Finished executing possible parts: {part_description}")
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
                f"Received a {MessageType.SIMULATION_STEP} message from client {client_id} with a wrong correlation_id. "
                + f"Expected {self._current_step} but got {received_message.message.correlation_id()}",
            )
            return False
        sim_step_data: ClientSimStepData = received_message.payload(
            ClientSimStepData,
        )
        SimulationExecutor.logger.debug(
            f"Processing a message containing a simulation step from client {client_id} on step {self._current_step}: {sim_step_data}",
        )
        interface_values = tuple(sim_step_data.interface_values)
        self._value_history.add(
            time_step=self._current_step,
            client_id=client_id,
            interface_values=interface_values + tuple(ready_for_execution_data_by_clients[client_id]),
        )
        self._current_step_data.add_received_data(client_id, interface_values)
        SimulationExecutor.logger.debug(
            f"Processing a message containing a simulation step from client {client_id} on step {self._current_step}: {sim_step_data}: DONE",
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
        SimulationExecutor.logger.debug(f"Rendering images at {step}")
        end_event = self._rendering_socket.request_and_send_images(step)
        if wait_for_finish_timeout is not None:
            end_event.wait(wait_for_finish_timeout)

    def force_stop(self) -> None:
        if self._server_state.is_running():
            SimulationExecutor.logger.debug("Executing force shutdown")
            self._server_state.force_stop()
