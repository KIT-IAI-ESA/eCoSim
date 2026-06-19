import threading
import dask.distributed as dd
from distributed.protocol import serialize, deserialize
import uuid
from abc import abstractmethod, ABC
from typing import override

from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.channel.esp_channel_endpoint import ESPChannelEndpoint, ConnectionData
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson

from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.socket.endpoint_socket import EndpointSocket
from ecosim_common.communication.dask.endpoint_dask import EndpointDask
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.data.simulation_setup_message import SimulationSetupMessage
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_server.client_connection import ClientConnection
from ecosim_server.data.repositories import Repositories
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.server_state import ServerState, ServerStateDask
from ecosim_server.simulation.rendering.rendering_socket import RenderingSocket
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.class_serializer import serialize_classes


class AbstractServer(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def print_measurement_statistics(self) -> None:
        pass

    @abstractmethod
    def force_stop(self) -> None:
        pass


class Server(AbstractServer, ShutdownListener):
    _logger = ESPLogger("Server")

    def __init__(
        self,
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
        repositories: Repositories,
    ):
        self.server_measurements = ServerTimeMeasurement()
        self._simulation_config: SimulationConfig = simulation_config
        self._server_config: ServerConfig = server_config
        self._server_state: ServerState = ServerState(
            simulation_config=simulation_config,
            simulation_state_repository=repositories.simulation_state_repository,
        )
        self._simulation_executor: SimulationExecutor = SimulationExecutor(
            simulation_config=self._simulation_config,
            server_config=self._server_config,
            server_state=self._server_state,
            repositories=repositories,
            server_measurement=self.server_measurements,
        )
        self._channel_endpoint: ESPChannelEndpoint = EndpointSocket(
            _connection_address=self._server_config.server.connection_address(),
        )
        self._rendering_socket: RenderingSocket | None = None
        self._repositories = repositories
        ShutdownManager().register_listener(self)

    @override
    def start(self) -> None:
        self._logger.info("Starting server")
        self._start_image_renderer_socket()
        self.server_measurements.set_start(ServerTimeMeasurementType.SERVER_UPTIME)
        self._simulation_config.print_for_start_up()
        self._server_config.print_config_for_start_up()
        self._channel_endpoint.listen_async(
            on_new_channel=self._handle_new_channel,
        )
        Server._logger.info("Waiting for all clients to connect...")
        self._server_state.wait_for_all_clients_connected_and_ready()
        Server._logger.info("All clients connected - starting simulation")
        self._server_state.set_simulation_state(SimulationState.READY)
        self._simulation_executor.execute(rendering_socket=self._rendering_socket)
        self._stop_image_renderer_socket()
        self._channel_endpoint.close()

    def _handle_new_channel(
        self,
        connection_data: ConnectionData,
    ) -> None:
        client_thread = threading.Thread(
            target=self._handle_client,
            args=(
                ClientConnection(
                    address=connection_data.client_address,
                    _channel=connection_data.channel,
                ),
            ),
        )
        client_thread.start()

    def _handle_client(
        self,
        connection: ClientConnection,
    ) -> None:
        client_id: ClientID | None = None
        with connection:
            try:
                Server._logger.debug("Handling new client connection")

                connection.send(ESPChannelMessageJson.empty(type=MessageType.CLIENT_META_DATA_REQUEST))

                message = connection.receive(expected_type=MessageType.CLIENT_META_DATA_REQUEST)
                if message is None:
                    raise Exception(f"No message received from client {client_id}")
                client_config: ClientMetaData = message.payload(ClientMetaData)
                if not self._server_state.client_states.add_if_needed(client_config, connection):
                    Server._logger.warning(
                        f"Client {connection.address} was not expected to connect - it has no needed model/simulator.",
                    )
                    connection.close()
                    return
                client_id = client_config.client_id()

                self._handle_interface_request(client_id, connection)
                self._handle_interface_settings(client_id, connection)
                self._handle_simulation_setup(client_id, connection)

                self._server_state.client_states.set_client_ready_for_simulation(
                    client_id,
                )

                while (
                    self._server_state.is_running()
                    and self._server_state.client_states.is_connected(client_id)
                ):
                    received_message = connection.receive()
                    if received_message is None:
                        Server._logger.warning(
                            f"Received 'none' from client {client_id}.",
                        )
                        continue
                    self._server_state.message_buffer.add(
                        client_id=client_id,
                        message=received_message,
                    )

            except Exception as e:
                connection.close()
                if client_id:
                    self._server_state.client_states.reset_state(client_id)
                raise e

    def _handle_simulation_setup(
        self,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        connection.send(
            ESPChannelMessageJson.create(
                type=MessageType.SIMULATION_SETUP,
                payload=SimulationSetupMessage(
                    step_size_in_ms=self._simulation_config.step_size_in_ms,
                ),
            ),
        )
        Server._logger.debug(f"Client {connection.address} accepted step size")
        self._server_state.client_states.step_size_accepted(client_id)

    def _handle_interface_settings(
        self,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        client_simulator_config = self._simulation_config.client_simulator_config_for(
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
        Server._logger.debug(f"Client {connection.address} accepted interface settings")

    def _handle_interface_request(
        self,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        connection.send(ESPChannelMessageJson.empty(type=MessageType.INTERFACE_REQUEST))
        message = connection.receive(expected_type=MessageType.INTERFACE_REQUEST)
        if message is None:
            raise Exception(f"No message received from client {client_id}")
        client_interfaces = message.payload(ModelInterfaceIds)
        if not self._simulation_config.validate_interfaces(
            client_id,
            client_interfaces,
        ):
            raise Exception(
                f"Client {connection.address} does not full-fill interface requirements. Please check previous logs for more details.",
            )
        Server._logger.debug(
            f"Successfully validated interfaces for client {connection.address}",
        )
        self._server_state.client_states.interfaces_validated(client_id)

    @override
    def print_measurement_statistics(self) -> None:
        self.server_measurements.print_statistics()

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
                + f"Port: {socket_port} | Interval: {rendering_interval} -> no socket will be opened.",
            )
            return
        SimulationExecutor.logger.info(
            f"Image renderer socket will be opened at port {socket_port}",
        )
        self._rendering_socket = RenderingSocket(
            host=self._server_config.server.host,
            port=socket_port,
        )
        started_event = self._rendering_socket.start()
        timeout = 5
        if not started_event.wait(timeout=timeout):
            SimulationExecutor.logger.warning(
                f"The rendering image socket did not start within {timeout}s -> the execution continues "
                + "but you may not be able to receive rendered images.",
            )

    def _stop_image_renderer_socket(self) -> None:
        if self._rendering_socket is None:
            return
        SimulationExecutor.logger.info("Stopping image renderer socket.")
        self._rendering_socket.close()

    @override
    def on_app_shutdown(self) -> None:
        self._channel_endpoint.close()
        self._stop_image_renderer_socket()

    @override
    def force_stop(self) -> None:
        self.on_app_shutdown()
        self._simulation_executor.force_stop()


# TODO_AFTER_MERGE: extract to custom package/file
# TODO_AFTER_MERGE: extract common functionality into AbstractServer / find abstractions
class Dask_Server(AbstractServer, ShutdownListener):
    _logger = ESPLogger("Server")

    def __init__(
        self,
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
        repositories: Repositories,
    ):
        self.server_measurements = ServerTimeMeasurement()
        self._simulation_config: SimulationConfig = simulation_config
        self._server_config: ServerConfig = server_config
        self._server_state: ServerStateDask = ServerStateDask(
            simulation_config=simulation_config,
        )
        self._simulation_executor: SimulationExecutor = SimulationExecutor(
            simulation_config=self._simulation_config,
            server_config=self._server_config,
            server_state=self._server_state,
            repositories=repositories,
            server_measurement=self.server_measurements,
            using_dask=True,
        )
        self._channel_endpoint: ESPChannelEndpoint = EndpointDask(
            _connection_address=self._server_config.server.connection_address(),
        )
        self._rendering_socket: RenderingSocket | None = None
        self._repositories = repositories
        serialize_classes()
        dask_client = dd.get_client()
        dask_client.run(serialize_classes)
        ShutdownManager().register_listener(self)

    @override
    def start(self) -> None:
        self._logger.info("Starting server")
        self._start_image_renderer_socket()
        self.server_measurements.set_start(ServerTimeMeasurementType.SERVER_UPTIME)
        self._simulation_config.print_for_start_up()
        self._server_config.print_config_for_start_up()
        server_state = dd.Queue("server_state")
        server_state.put(serialize(self._server_state))
        self._channel_endpoint.listen_async(
            on_new_channel=ChannelHandling(simulation_config=self._simulation_config)._handle_new_channel,      #
        )
        Server._logger.info("Waiting for all clients to connect...")

        while not self._server_state.are_all_clients_connected_and_ready():
            self._server_state = deserialize(*server_state.get())
            server_state.put(serialize(self._server_state))

        Server._logger.info("All clients connected - starting simulation")
        self._server_state = deserialize(*server_state.get())
        self._set_simulation_state(SimulationState.READY)
        server_state.put(serialize(self._server_state))
        self._simulation_executor.execute(rendering_socket=self._rendering_socket)
        self._stop_image_renderer_socket()
        self._channel_endpoint.close()
        while server_state.qsize() > 0:
            server_state.get()

    @override
    def print_measurement_statistics(self) -> None:
        self.server_measurements.print_statistics()

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
                + f"Port: {socket_port} | Interval: {rendering_interval} -> no socket will be opened.",
            )
            return
        SimulationExecutor.logger.info(
            f"Image renderer socket will be opened at port {socket_port}",
        )
        self._rendering_socket = RenderingSocket(
            host=self._server_config.server.host,
            port=socket_port,
        )
        started_event = self._rendering_socket.start()
        timeout = 5
        if not started_event.wait(timeout=timeout):
            SimulationExecutor.logger.warning(
                f"The rendering image socket did not start within {timeout}s -> the execution continues "
                + "but you may not be able to receive rendered images.",
            )

    def _stop_image_renderer_socket(self) -> None:
        if self._rendering_socket is None:
            return
        SimulationExecutor.logger.info("Stopping image renderer socket.")
        self._rendering_socket.close()

    def _set_simulation_state(self, simulation_state: SimulationState) -> None:
        self._repositories.simulation_state_repository.update(simulation_state)

    @override
    def on_app_shutdown(self) -> None:
        if self._repositories.simulation_state_repository.current() != SimulationState.FINISHED:
            self._set_simulation_state(SimulationState.FAILED)
        self._channel_endpoint.close()
        self._stop_image_renderer_socket()

    @override
    def force_stop(self) -> None:
        self.on_app_shutdown()
        self._simulation_executor.force_stop()


class ChannelHandling():

    def __init__(
        self,
        simulation_config: SimulationConfig,
    ) -> None:
        server_state = dd.Queue("server_state")
        self._server_state: ServerState = deserialize(*server_state.get())
        server_state.put(serialize(self._server_state))
        self._simulation_config = simulation_config

    def _handle_new_channel(
        self,
        connection_data: ConnectionData,
    ) -> None:
        dd_client = dd.get_client()

        async def async_handle() -> None:
            future = dd_client.submit(
                self._handle_client,
                ClientConnection(
                    address=connection_data.client_address,
                    _channel=connection_data.channel,
                ),
                key=uuid.uuid4().hex,
            )
            dd.fire_and_forget(future)
        dd_client.sync(async_handle)

    def _handle_client(
        self,
        connection: ClientConnection,
    ) -> None:
        client_id: ClientID | None = None
        dd.get_client()
        dd.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
        with connection:
            server_state = dd.Queue("server_state")
            try:
                Server._logger.debug("Handling new client connection")
                self._server_state = deserialize(*server_state.get())
                connection.send(ESPChannelMessageJson.empty(type=MessageType.CLIENT_META_DATA_REQUEST))
                message = connection.receive(expected_type=MessageType.CLIENT_META_DATA_REQUEST)
                if message is None:
                    raise Exception(f"No message received from client {client_id}")
                client_config: ClientMetaData = message.payload(ClientMetaData)
                if not self._server_state.client_states.add_if_needed(client_config, connection):
                    Server._logger.warning(
                        f"Client {connection.address} was not expected to connect - it has no needed model/simulator.",
                    )
                    connection.close()
                    return
                client_id = client_config.client_id()

                self._handle_interface_request(client_id, connection)
                self._handle_interface_settings(client_id, connection)
                self._handle_simulation_setup(client_id, connection)

                self._server_state.client_states.set_client_ready_for_simulation(
                    client_id,
                )
                server_state.put(serialize(self._server_state))
                calls = 0  # Terminate server if no clients are connected after queue timeout
                while (
                    self._server_state.is_running()
                    and self._server_state.client_states.is_connected(client_id)
                ):
                    # self._server_state = server_state.get()
                    # server_state.put(self._server_state)
                    received_message = connection.receive()

                    if received_message is None:
                        Server._logger.warning(
                            f"Received 'none' from client {client_id}.",
                        )
                        calls += 1
                        if dd.Event(name="global_finish").is_set():
                            connection.close()
                            # connection.close()
                            # self._server_state = deserialize(*server_state.get())
                            # self._server_state.force_stop()
                            # dd.Event(name="stop_execution").set()
                            # server_state.put(serialize(self._server_state))
                        continue
                    self._server_state = deserialize(*server_state.get())
                    self._server_state.message_buffer.add(
                        client_id=client_id,
                        message=received_message,
                    )
                    server_state.put(serialize(self._server_state))

            except Exception as e:
                connection.close()
                if client_id:
                    self._server_state = deserialize(*server_state.get())
                    self._server_state.client_states.reset_state(client_id)
                    server_state.put(serialize(self._server_state))
                raise e

    def _handle_simulation_setup(
        self,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        connection.send(
            ESPChannelMessageJson.create(
                type=MessageType.SIMULATION_SETUP,
                payload=SimulationSetupMessage(
                    step_size_in_ms=self._simulation_config.step_size_in_ms,
                ),
            ),
        )
        connection.receive(expected_type=MessageType.SIMULATION_SETUP)
        Server._logger.debug(f"Client {connection.address} accepted step size")
        self._server_state.client_states.step_size_accepted(client_id)

    def _handle_interface_settings(
        self,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        client_simulator_config = self._simulation_config.client_simulator_config_for(
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
        Server._logger.debug(f"Client {connection.address} accepted interface settings")

    def _handle_interface_request(
        self,
        client_id: ClientID,
        connection: ClientConnection,
    ) -> None:
        connection.send(ESPChannelMessageJson.empty(type=MessageType.INTERFACE_REQUEST))
        message = connection.receive(expected_type=MessageType.INTERFACE_REQUEST)
        if message is None:
            raise Exception(f"No message received from client {client_id}")
        client_interfaces = message.payload(ModelInterfaceIds)
        if not self._simulation_config.validate_interfaces(
            client_id,
            client_interfaces,
        ):
            raise Exception(
                f"Client {connection.address} does not full-fill interface requirements. Please check previous logs for more details.",
            )
        Server._logger.debug(
            f"Successfully validated interfaces for client {connection.address}",
        )
        self._server_state.client_states.interfaces_validated(client_id)
