from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import ClassVar, override

from ecosim_common.communication.channel.esp_channel import ConnectionData, ESPChannel
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.data.simulation_setup_message import SimulationSetupMessage
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.server_state import ServerState
from ecosim_server.simulation.rendering.rendering_socket import RenderingSocket
from ecosim_server.simulation.response_timeouts import ResponseTimeouts
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from ecosim_server.simulation.state.simulation_state import SimulationState


@dataclass
class Server(ShutdownListener):
    _logger: ClassVar[ESPLogger] = ESPLogger("Server")

    server_measurements: ServerTimeMeasurement = field(init=False)

    _simulation_config: SimulationConfig = field()
    _server_config: ServerConfig = field()
    _repositories: Repositories = field()
    _response_timeouts: ResponseTimeouts = field(default_factory=ResponseTimeouts)

    _client_communication: ClientCommunication = field(init=False)
    _server_state: ServerState = field(init=False)
    _simulation_executor: SimulationExecutor = field(init=False)
    _channel: ESPChannel = field(init=False)
    _rendering_socket: RenderingSocket | None = field(init=False)

    def __post_init__(self) -> None:
        self.server_measurements = ServerTimeMeasurement(protocol=self._server_config.server.communication_protocol)
        self._server_state: ServerState = ServerState.of(
            server_config=self._server_config,
            simulation_state_repository=self._repositories.simulation_state_repository,
        )
        self._client_communication = ClientCommunication.of(
            server_config=self._server_config,
            simulation_config=self._simulation_config,
        )
        self._simulation_executor: SimulationExecutor = SimulationExecutor(
            simulation_config=self._simulation_config,
            server_config=self._server_config,
            server_state=self._server_state,
            repositories=self._repositories,
            server_measurement=self.server_measurements,
            client_communication=self._client_communication,
            response_timeouts=self._response_timeouts,
        )
        self._channel: ESPChannel = ESPChannel.for_protocol(
            communication_protocol=self._server_config.server.communication_protocol,
            connection_address=self._server_config.server.connection_address(),
        )
        self._rendering_socket: RenderingSocket | None = None
        ShutdownManager().register_listener(self)

    def start(self) -> None:
        self._logger.info("Starting server")
        self._start_image_renderer_socket()
        self.server_measurements.set_start(ServerTimeMeasurementType.SERVER_UPTIME)
        self._simulation_config.print_for_start_up()
        self._server_config.print_config_for_start_up()
        self._start_listening()
        self._wait_for_all_clients_connected_and_ready()
        self._logger.info("All clients connected - starting simulation")
        self._server_state.set_simulation_state(SimulationState.READY)
        self._simulation_executor.execute(rendering_socket=self._rendering_socket)
        self._stop_image_renderer_socket()
        self._channel.close()

    def _start_listening(self) -> None:
        self._channel.listen_on_connection_loop_async(
            channel_handler=partial(
                Server._on_new_channel,
                self._server_state.is_running_event(),
                self._client_communication,
                self._simulation_config,
            ),
        )

    def _wait_for_all_clients_connected_and_ready(self) -> None:
        self._logger.info("Waiting for all clients to connect...")
        self._client_communication.wait_for_all_clients_connected_and_ready()

    def print_measurement_statistics(self) -> None:
        self.server_measurements.print_statistics()

    def force_stop(self) -> None:
        self.on_app_shutdown()
        self._simulation_executor.force_stop()

    @override
    def on_app_shutdown(self) -> None:
        if self._repositories.simulation_state_repository.current() != SimulationState.FINISHED:
            self._server_state.set_simulation_state(SimulationState.FAILED)
        self._channel.close()
        self._stop_image_renderer_socket()

    def _stop_image_renderer_socket(self) -> None:
        if self._rendering_socket is None:
            return
        SimulationExecutor.logger.info("Stopping image renderer socket.")
        self._rendering_socket.close()

    @staticmethod
    def handle_simulation_setup(
        client_communication: ClientCommunication,
        simulation_config: SimulationConfig,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        connection.send(
            ESPChannelMessageJson.create(
                type=MessageType.SIMULATION_SETUP,
                payload=SimulationSetupMessage(
                    step_size_in_ms=simulation_config.step_size_in_ms,
                ),
            ),
        )
        connection.receive(expected_type=MessageType.SIMULATION_SETUP)
        Server._logger.debug("Client %s accepted step size", connection.address)
        client_communication.step_size_accepted(client_id)

    @staticmethod
    def handle_interface_settings(
        simulation_config: SimulationConfig,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        client_simulator_config = simulation_config.client_simulator_config_for(
            client_id,
        )
        if client_simulator_config is None:
            raise Exception(
                f"No simulator configuration available for client {connection.address}.",
            )
        connection.send(
            ESPChannelMessageJson.create(
                type=MessageType.INTERFACE_SETTINGS,
                payload=client_simulator_config.to_server_interface_settings(),
            ),
        )
        connection.receive(expected_type=MessageType.INTERFACE_SETTINGS)
        Server._logger.debug("Client %s accepted interface settings", connection.address)

    @staticmethod
    def handle_interface_request(
        client_communication: ClientCommunication,
        simulation_config: SimulationConfig,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        connection.send(ESPChannelMessageJson.empty(type=MessageType.INTERFACE_REQUEST))
        message = connection.receive(expected_type=MessageType.INTERFACE_REQUEST)
        client_interfaces = message.payload(ModelInterfaceIds)
        if not simulation_config.validate_interfaces(
            client_id,
            client_interfaces,
        ):
            raise Exception(
                f"Client {connection.address} does not full-fill interface requirements. Please check previous logs for more details.",
            )
        Server._logger.debug("Successfully validated interfaces for client %s", connection.address)
        client_communication.interfaces_validated(client_id)

    def _start_image_renderer_socket(self) -> None:
        rendering_interval = self._server_config.server.image_renderer_interval
        socket_port = self._server_config.server.image_renderer_port
        if rendering_interval is None and socket_port is None:
            SimulationExecutor.logger.info(
                "No image renderer config is set - so no rendering socket will be opened.",
            )
            return
        if socket_port is None or rendering_interval is None:
            SimulationExecutor.logger.error(
                "Invalid configuration for image renderer, since only either port or interval is set (and not both). "
                "Port: %s | Interval: %s -> no socket will be opened.",
                socket_port,
                rendering_interval,
            )
            return
        SimulationExecutor.logger.info("Image renderer socket will be opened at port %s", socket_port)
        self._rendering_socket = RenderingSocket(
            host=self._server_config.server.host,
            port=socket_port,
        )
        started_event = self._rendering_socket.start()
        timeout = 5
        if not started_event.wait(timeout=timeout):
            SimulationExecutor.logger.warning(
                "The rendering image socket did not start within %ss -> the execution continues but you may not be able to receive rendered images.",
                timeout,
            )

    @staticmethod
    def handle_client(
        server_running_event: ParallelEvent,
        client_communication: ClientCommunication,
        simulation_config: SimulationConfig,
        connection: ClientConnection,
    ) -> None:
        with connection:
            client_id: ClientID | None = None
            try:
                Server._logger.debug("Handling new client connection")
                connection.send(ESPChannelMessageJson.empty(type=MessageType.CLIENT_META_DATA_REQUEST))
                message = connection.receive(expected_type=MessageType.CLIENT_META_DATA_REQUEST)
                client_config: ClientMetaData = message.payload(ClientMetaData)
                client_id = client_config.client_id()
                if not client_communication.add_if_needed(client_config, connection):
                    Server._logger.warning(
                        "Client %s from %s was not expected to connect - it has no needed model/simulator.",
                        client_id,
                        connection.address,
                    )
                    connection.close()
                    return

                Server.handle_interface_request(client_communication, simulation_config, client_id, connection)
                Server.handle_interface_settings(simulation_config, client_id, connection)
                Server.handle_simulation_setup(client_communication, simulation_config, client_id, connection)

                client_communication.set_client_ready_for_simulation(
                    client_id,
                )
                while server_running_event.is_set():
                    received_message = connection.receive()
                    if received_message is None:
                        Server._logger.warning("Received 'none' from client %s -> this is the closing signal -> ending this connection", client_id)
                        client_communication.set_client_connected_state(client_id=client_id, connected=False)
                        return
                    client_communication.add_message_from_client(client_id, received_message)

            except Exception as e:
                connection.close()
                if client_id:
                    client_communication.reset_state(client_id)
                raise e

    @staticmethod
    def _on_new_channel(
        server_running_event: ParallelEvent,
        client_communication: ClientCommunication,
        simulation_config: SimulationConfig,
        connection_data: ConnectionData,
    ) -> None:
        Server.handle_client(
            server_running_event=server_running_event,
            client_communication=client_communication,
            simulation_config=simulation_config,
            connection=ClientConnection(
                address=connection_data.client_address,
                _channel=connection_data.channel,
            ),
        )
