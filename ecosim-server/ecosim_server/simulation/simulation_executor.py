from __future__ import annotations
import threading
import dask.distributed as dd
from distributed.protocol import serialize, deserialize

import time
import sys
from time import sleep
from datetime import datetime
from functools import partial
from typing import List, Any

from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.data.repositories import Repositories
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.message_buffer import BufferedClientMessage
from ecosim_server.server_state import ServerState, ServerStateDask
from ecosim_server.simulation.current_step_data import CurrentStepData
from ecosim_server.simulation.interface_value_history import InterfaceValueHistory
from ecosim_server.simulation.rendering.rendering_socket import RenderingSocket
from ecosim_server.simulation.state.simulation_state import SimulationState


class SimulationExecutor:
    logger = ESPLogger("SimulationExecutor")

    def __init__(
        self,
        simulation_config: SimulationConfig,
        server_config: ServerConfig,
        server_state: ServerState | ServerStateDask,
        repositories: Repositories,
        server_measurement: ServerTimeMeasurement,
        using_dask: bool = False,
    ):
        self.simulation_config = simulation_config
        self._server_config = server_config
        self._server_state = server_state
        self._current_step: int = 0
        self._value_history = InterfaceValueHistory(repositories, simulation_config)
        self._client_communication: ClientCommunication = ClientCommunication(
            client_states=server_state.client_states,
            client_message_buffer=server_state.message_buffer,
        )
        self._current_step_data = CurrentStepData(simulation_config)
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
        self._using_dask = using_dask
        if using_dask:
            self._state_variable = dd.Queue("server_state")
            self._sim_repo = repositories.simulation_state_repository

    def execute(
        self,
        rendering_socket: RenderingSocket | None,
    ) -> None:
        self._rendering_socket = rendering_socket
        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
            self._state_variable.put(serialize(self._server_state))
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
        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
        SimulationExecutor.logger.info("Sending 'stop simulation' signal to all clients")
        self._server_state.set_is_finished(True)
        if self._using_dask:
            self._state_variable.put(serialize(self._server_state))
            self._sim_repo.update(SimulationState.FINISHED)
        self._handle_image_renderer(wait_for_finish_timeout=9)

        self._client_communication.broadcast(ESPChannelMessageJson.empty(type=MessageType.SIMULATION_STOP))
        while not self._server_state.have_all_clients_stopped_simulation():
            if self._using_dask:
                self._server_state = deserialize(*self._state_variable.get())
                self._update_client_communication()
            for message in self._client_communication.messages_of(
                client_ids=self._server_state.client_states.all_client_ids(),
                message_types=(MessageType.SIMULATION_STOP,),
            ):
                self._server_state.client_states.simulation_stopped(
                    client_id=message.client_id,
                )
            if self._using_dask:
                self._state_variable.put(serialize(self._server_state))
            if not self._using_dask:
                sleep(2)
        SimulationExecutor.logger.info("All clients stopped (or are not connected anymore)")

    def _start_simulation_of_all_clients(
        self,
        store_default_values_in_history: bool = True,
    ) -> None:
        SimulationExecutor.logger.info(
            "Starting simulation on all clients and wait for successful start",
        )
        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
            self._state_variable.put(serialize(self._server_state))
        self._client_communication.broadcast(
            ESPChannelMessageJson.empty(type=MessageType.SIMULATION_START),
        )
        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
            self._state_variable.put(serialize(self._server_state))
        while ((not self._server_state.have_all_clients_started_simulation()) and
               self._server_state.are_all_clients_connected_and_ready()):
            if self._using_dask:
                self._server_state = deserialize(*self._state_variable.get())
                self._update_client_communication()
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
            if self._using_dask:
                self._state_variable.put(serialize(self._server_state))
                # In case of XMLParseError during initialization, break the loop
                if dd.Event(name="global_finish").is_set():
                    SimulationExecutor.logger.error("Error occured when starting simulators. Exitting...")
                    self.force_stop()
                    sys.exit(1)
            if not self._using_dask:
                sleep(2)
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

        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
            self._state_variable.put(serialize(self._server_state))
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
            if self._using_dask:
                responses: dict[Any, dd.Event | threading.Event] = {
                    client_id: dd.Event(name=client_id)
                    for client_id in self.simulation_config.client_ids()
                }

            else:
                responses = {client_id: threading.Event() for client_id in self.simulation_config.client_ids()}

            def handle_batch_response(message: BufferedClientMessage) -> None:
                client_id = message.client_id
                if message.message.correlation_id() != CorrelationId.of_date_time(start_date):
                    self.logger.error(
                        f"Received a {MessageType.SIMULATION_STEP_BATCH} message from client {client_id} with a wrong correlation_id. "
                        + f"Expected response for start date {start_date} but got {message.message.correlation_id()}",
                    )
                    return
                responses[client_id].set()

            if self._using_dask:
                # while len(self._server_state.message_buffer._buffer) < len(handled_client_ids):
                #     self._server_state = self._state_variable.get()
                #     self._update_client_communication()
                #     self._state_variable.put(self._server_state)
                self._server_state = deserialize(*self._state_variable.get())
                self._update_client_communication()
                self._client_communication.on_messages(
                    client_ids=tuple(handled_client_ids),
                    message_types=(MessageType.SIMULATION_STEP_BATCH,),
                    callback=partial(
                        _handle_batch_response_dask,
                        start_date=start_date,
                    ),
                )
                self._state_variable.put(serialize(self._server_state))

            else:
                self._client_communication.on_messages(
                    client_ids=tuple(handled_client_ids),
                    message_types=(MessageType.SIMULATION_STEP_BATCH,),
                    callback=handle_batch_response,
                )

            for client_id, event in responses.items():
                if not event.wait(timeout=60 * 60):
                    raise RuntimeError(f"Timeout while waiting for restore response from client {client_id}")

            if self._using_dask:
                self._server_state = deserialize(*self._state_variable.get())
                self._update_client_communication()
            self._client_communication.remove_on_message_callback(
                client_ids=self.simulation_config.client_ids(),
                message_types=(MessageType.SIMULATION_STEP_BATCH,),
            )
            if self._using_dask:
                self._state_variable.put(serialize(self._server_state))
        SimulationExecutor.logger.info(
            f"[Restore simulation] Restoring simulation on all clients successful - continuing from step {self._current_step}.",
        )

    def _execute_steps(self) -> None:
        self.logger.debug("Executing steps")
        if self._using_dask:
            current_step_data_queue = dd.Queue(name="step_data")
            if current_step_data_queue.qsize() > 0:
                # empty queue when executed in test framework
                _ = current_step_data_queue.get()
            current_step_data_queue.put(serialize(self._current_step_data))
        while self._current_step < self.simulation_config.steps:
            self.logger.info(f"Step {self._current_step}: Executing step {self._current_step}")
            if self._using_dask:
                self._current_step_data = deserialize(*current_step_data_queue.get())
            self._current_step_data.reset_for_new_step(step=self._current_step)
            self._execute_logical_delays()
            if self._using_dask:
                current_step_data_queue.put(serialize(self._current_step_data))

            # TODO: change to a waiting mechanism
            while not self._current_step_data.all_clients_executed():
                self._execute_possible_parts("Periodic possible parts execution")
                if self._using_dask:
                    handled_clients_queue = dd.Queue(name="handled_clients", maxsize=1)
                    # Clear queue from previous iteration
                    if handled_clients_queue.qsize() == 1:
                        handled_clients_queue.get()
                if not self._current_step_data.all_clients_executed():
                    self.logger.debug(
                        f"Step {self._current_step}: Waiting for all clients to be executed in a 'possible parts' execution",
                    )

                if self._using_dask:
                    if dd.Event(name="global_finish").is_set():
                        SimulationExecutor.logger.error("Error occured while running simulators. Exitting...")
                        self.force_stop()
                        sys.exit(1)

            self._handle_image_renderer()
            self._current_step += 1
            if self._using_dask:
                handled_clients_queue = dd.Queue(name="handled_clients", maxsize=1)
                # Clear queue from previous iteration
                if handled_clients_queue.qsize() == 1:
                    handled_clients_queue.get()

    def _execute_logical_delays(self) -> None:
        self.logger.debug(f"Step {self._current_step}: Execute logical delays")
        delays_by_delay_step = self._current_step_data.logical_delays_by_delay_step()
        for delayed_time_steps in sorted(delays_by_delay_step.keys()):
            self.logger.info(f"Step {self._current_step}: Execute logical delays at '{delayed_time_steps}'")
            for logical_delay_connection in delays_by_delay_step[delayed_time_steps].connections:
                self.logger.debug(
                    f"Step {self._current_step}: Execute logical delay '{delayed_time_steps}': " +
                    f"{logical_delay_connection.output_interface} -> {logical_delay_connection.current_value}",
                )
                self._current_step_data.set_value(
                    logical_delay_connection.output_interface,
                    logical_delay_connection.current_value,
                )

    def _execute_possible_parts(
        self,
        part_description: str,
    ) -> None:
        if self._using_dask:
            current_step_data_queue = dd.Queue(name="step_data")
            self._current_step_data = deserialize(*current_step_data_queue.get())
        ready_for_execution_data_by_clients: dict[
            ClientID,
            List[ProtocolInterfaceValue],
        ] = self._current_step_data.get_ready_for_execution()
        if self._using_dask:
            current_step_data_queue.put(serialize(self._current_step_data))
        self.logger.info(
            f"Step {self._current_step}: Execute possible parts: {part_description} - {len(ready_for_execution_data_by_clients)} clients are ready:" +
            f" {', '.join(str(client_id) for client_id in ready_for_execution_data_by_clients.keys())}",
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
        if self._using_dask:
            handled_clients_queue = dd.Queue(name="handled_clients", maxsize=1)
            handled_clients_queue.put(serialize(handled_clients))

        client_ids = tuple(handled_clients.keys())
        if len(handled_clients) == 0:
            self.logger.debug(
                f"Step {self._current_step}: Executing possible parts: {part_description}: Nothing to do.",
            )
            return

        message_types = (MessageType.SIMULATION_STEP,)
        all_clients_handled_event = threading.Event()

        if self._using_dask:
            # This while loop can take between 0.03 and 0.13 seconds to complete.
            # Might need to look into alternative.
            # while len(self._server_state.message_buffer._buffer) < len(client_ids):
            #     self._server_state = self._state_variable.get()
            #     self._update_client_communication()
            #     self._state_variable.put(self._server_state)
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
            all_clients_handled_dask = dd.Event(name="clients_handled")

            self._client_communication.on_messages(
                client_ids=client_ids,
                message_types=message_types,
                callback=partial(
                    _handle_received_sim_step_dask,
                        ready_for_execution_data_by_clients=serialize(ready_for_execution_data_by_clients),
                        current_step=self._current_step,
                ),
            )
            self._state_variable.put(serialize(self._server_state))
        else:
            self._client_communication.on_messages(
                client_ids=client_ids,
                message_types=message_types,
                callback=lambda message: self._handle_received_sim_step(
                    message,
                    handled_clients=handled_clients,
                    ready_for_execution_data_by_clients=ready_for_execution_data_by_clients,
                    all_clients_handled_event=all_clients_handled_event,
                ),
            )
        self.logger.debug(
            f"Step {self._current_step}: Waiting for results after executing possible parts: {part_description}",
        )

        if self._using_dask:
            all_clients_handled_dask.wait()
            all_clients_handled_dask.clear()
            value_queue = dd.Queue("values_for_history")
            thread_list = []

            while value_queue.qsize() > 0:
                value = value_queue.get()
                thread = threading.Thread(target=self._value_history.add, args=[self._current_step, deserialize(*value[0]), deserialize(*value[1])])
                thread_list.append(thread)
            for thread in thread_list:
                thread.start()

        else:
            all_clients_handled_event.wait()

        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
        self._client_communication.remove_on_message_callback(client_ids, message_types)
        if self._using_dask:
            self._state_variable.put(serialize(self._server_state))

        if self._using_dask:
            self._current_step_data = deserialize(*current_step_data_queue.get())
        for client in handled_clients:
            self._current_step_data.set_is_executed(client)
        if self._using_dask:
            current_step_data_queue.put(serialize(self._current_step_data))

        self.logger.debug(f"Finished executing possible parts: {part_description}")

    def _handle_received_sim_step(
        self,
        received_message: BufferedClientMessage,
        ready_for_execution_data_by_clients: dict[ClientID, List[ProtocolInterfaceValue]],
        handled_clients: dict[ClientID, bool],
        all_clients_handled_event: threading.Event,
    ) -> None:
        client_id = received_message.client_id
        if received_message.message.correlation_id().to_int() != self._current_step:
            self.logger.error(
                f"Received a {MessageType.SIMULATION_STEP} message from client {client_id} with a wrong correlation_id. " +
                f"Expected {self._current_step} but got {received_message.message.correlation_id()}",
            )
            return
        client_sim_step_data: ClientSimStepData = received_message.payload(
            ClientSimStepData,
        )
        self._process_sim_step_message(
            client_id=client_id,
            sim_step_data=client_sim_step_data,
            ready_for_execution_data_by_clients=ready_for_execution_data_by_clients,
        )
        handled_clients[client_id] = True

        if all(handled_clients.values()):
            all_clients_handled_event.set()

    def _process_sim_step_message(
        self,
        client_id: ClientID,
        sim_step_data: ClientSimStepData,
        ready_for_execution_data_by_clients: dict[
            ClientID,
            List[ProtocolInterfaceValue],
        ],
    ) -> None:
        self.logger.debug(
            f"Processing a message containing a simulation step from client {client_id} on step {self._current_step}: {sim_step_data}",
        )
        interface_values = tuple(sim_step_data.interface_values)
        self._value_history.add(
            time_step=self._current_step,
            client_id=client_id,
            interface_values=interface_values + tuple(ready_for_execution_data_by_clients[client_id]),
        )
        self._current_step_data.add_received_data(client_id, interface_values)
        self.logger.debug(
            f"Processing a message containing a simulation step from client {client_id} on step {self._current_step}: {sim_step_data}: DONE",
        )

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
        if self._using_dask:
            self._server_state = deserialize(*self._state_variable.get())
            self._update_client_communication()
        if self._server_state.is_running():
            SimulationExecutor.logger.debug("Executing force shutdown")
            self._server_state.force_stop()
            if self._using_dask:
                self._state_variable.put(serialize(self._server_state))

    def _update_client_communication(self) -> None:
        self._client_communication = ClientCommunication(
            client_states=self._server_state.client_states,
            client_message_buffer=self._server_state.message_buffer,
        )


def _handle_received_sim_step_dask(
        received_message: BufferedClientMessage,
        ready_for_execution_data_by_clients: tuple[dict[str, Any], list[bytes | memoryview[int]]],
        current_step: int,
) -> None:
    ready_for_execution_data_by_clients_deserial: dict[ClientID, List[ProtocolInterfaceValue]] = deserialize(*ready_for_execution_data_by_clients)
    dd.get_client()
    client_id = received_message.client_id
    if received_message.message.correlation_id().to_int() != current_step:
        print(
            f"Received a {MessageType.SIMULATION_STEP} message from client {client_id} with a wrong correlation_id. " +
                f"Expected {current_step} but got {received_message.message.correlation_id()}",
        )
        return
    client_sim_step_data: ClientSimStepData = received_message.payload(
        ClientSimStepData,
    )

    print(
            f"Processing a message containing a simulation step from client {client_id} on step {current_step}: {client_sim_step_data}",
    )
    interface_values = tuple(client_sim_step_data.interface_values)
    value_queue = dd.Queue(name="values_for_history")
    current_step_data_queue = dd.Queue(name="step_data")
    handled_clients_queue = dd.Queue(name="handled_clients")

    value_queue.put((serialize(client_id), serialize(interface_values + tuple(ready_for_execution_data_by_clients_deserial[client_id]))))

    current_step_data: CurrentStepData = deserialize(*current_step_data_queue.get())
    current_step_data.add_received_data(client_id, interface_values)
    current_step_data_queue.put(serialize(current_step_data))
    print(
        f"Processing a message containing a simulation step from client {client_id} on step {current_step}: {client_sim_step_data}: DONE",
    )

    handled_clients = deserialize(*handled_clients_queue.get())
    handled_clients[client_id] = True
    handled_clients_queue.put(serialize(handled_clients))

    if all(handled_clients.values()):
        all_clients_handled = dd.Event(name="clients_handled")
        all_clients_handled.set()


def _handle_batch_response_dask(message: BufferedClientMessage, start_date: datetime) -> None:
    client_id = message.client_id
    if message.message.correlation_id() != CorrelationId.of_date_time(start_date):
        SimulationExecutor.logger.error(
            f"Received a {MessageType.SIMULATION_STEP_BATCH} message from client {client_id} with a wrong correlation_id. "
            + f"Expected response for start date {start_date} but got {message.message.correlation_id()}",
        )
        return
    dd.Event(name=client_id).set()

# def _lambda_dask(
#         ready_for_execution_data_by_clients: dict[ClientID, List[ProtocolInterfaceValue]],
#         handled_clients: dict[ClientID, bool],
#         current_step: int,
# ) -> Callable[[BufferedClientMessage],None]:
#     return _handle_received_sim_step_dask(ready_for_execution_data_by_clients=ready_for_execution_data_by_clients,
#                                           handled_clients=handled_clients,
#                                           current_step=current_step,
#                                           )
