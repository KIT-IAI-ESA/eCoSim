from abc import abstractmethod
from typing import Dict

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.client.renderer.rendering_socket_client import RenderingSocketClient
from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.socket.socket_connector import SocketConnector
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.communication.data.simulation_setup_message import SimulationSetupMessage
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


class Client(ShutdownListener):
    logger = ESPLogger("Client")

    def __init__(
        self,
        client_config: ClientConfig,
    ):
        self._client_config: ClientConfig = client_config
        self._client_config.print_to_info()
        self._execution_config: ExecutionConfig = ExecutionConfig()
        self._channel_connector: ESPChannelConnector = SocketConnector()
        self._channel_or_none: ESPChannel | None = None
        self._image_renderer_socket: RenderingSocketClient | None = None
        self._is_finished = False
        ShutdownManager().register_listener(self)

    @property
    def _channel(self) -> ESPChannel:
        if self._channel_or_none is None:
            raise RuntimeError("Channel is not initialized")
        return self._channel_or_none

    @property
    def client_id(self) -> ClientID:
        return self._client_config.client_id()

    @abstractmethod
    def on_simulation_start(self) -> ClientSimStepData:
        """
        You need to 'start' the simulation (e.g., set everything up) and return the default values for each output
        interface (i.e., the value on step 0).
        :return: The values on step 0
        """
        pass

    @abstractmethod
    def on_simulation_step(
        self,
        received_inputs: dict[InterfaceId, InterfaceValueType],
        step_size_in_seconds: float,
    ) -> ClientSimStepData:
        """
        You need to run the simulation for :step_size_in_seconds: and return the resulting values for each output
        interface.
        :return: The values after running the simulation for :step_size_in_seconds:
        """
        pass

    @abstractmethod
    def on_simulation_stop(self) -> None:
        pass

    @abstractmethod
    def image_renderer_service(self) -> SimulationRendererService:
        pass

    def start(self) -> None:
        Client.logger.info(
            "Starting to connect to " +
            f"{self._client_config.server_config().server_address.ip}:{self._client_config.server_config().server_address.port}",
        )
        self._connect_channel()
        self._channel.listen_async(
            on_message=self._handle_message,
        )

    def wait_until_finished(self) -> None:
        self._channel.wait_for_finish()

    def _connect_channel(
        self,
        timeout_in_seconds: int = 30,
    ) -> None:
        try:
            self._channel_or_none = self._channel_connector.connect(
                connection_address=self._client_config.server_config().server_address,
                timeout_in_seconds=timeout_in_seconds,
            )
        except ConnectionError as e:
            self.on_app_shutdown()
            raise e
        Client.logger.info(f"Connected to socket successfully: "
                           f"{self._client_config.server_config().server_address.ip}:{self._client_config.server_config().server_address.port}")

    def _handle_message(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug('Received and handling message')
        if message.type() == MessageType.CLIENT_META_DATA_REQUEST:
            Client.logger.debug('Handling poss config request')
            self._channel.send(
                ESPChannelMessageJson.answer_with_payload(
                    request_message=message,
                    payload=self._client_config.meta_data(),
                ),
            )
        elif message.type() == MessageType.INTERFACE_REQUEST:
            Client.logger.debug('Handling interface request')
            self._channel.send(
                ESPChannelMessageJson.answer_with_payload(
                    request_message=message,
                    payload=ModelInterfaceIds.of_interface_config(self._client_config),
                ),
            )
        elif message.type() == MessageType.INTERFACE_SETTINGS:
            Client.logger.debug('Handling interface settings')
            server_interface_settings: ServerInterfaceSettings = message.payload(ServerInterfaceSettings)

            # check if config matches actual interfaces
            config_validated = self._client_config.interfaces_config().validate_config_with_server(server_interface_settings)
            self._execution_config.set_server_interface_settings(server_interface_settings)

            error_occurred = not config_validated
            if error_occurred:
                Client.logger.error(
                    "   ->> Could not validate the incoming input/output interfaces - there seems to be a mismatch "
                    "between the client interfaces and the interfaces the server requires",
                )

            self._channel.send(ESPChannelMessageJson.empty_answer(message))

        elif message.type() == MessageType.SIMULATION_SETUP:
            Client.logger.debug('Handling simulation setup')
            self._execution_config.set_step_size_in_ms(message.payload(SimulationSetupMessage).step_size_in_ms)
            Client.logger.debug(f'  -> step size (in seconds): {self._execution_config.step_size_in_seconds()}')
            self._channel.send(ESPChannelMessageJson.empty_answer(message))

        elif message.type() == MessageType.SIMULATION_START:
            Client.logger.debug('Handling start simulation')
            data = self.on_simulation_start()
            self._channel.send(
                ESPChannelMessageJson.answer_with_payload(
                    request_message=message,
                    payload=data,
                ),
            )
            self._init_image_renderer_connection()

        elif message.type() == MessageType.SIMULATION_STEP:
            Client.logger.info('Handling simulation step')
            received_inputs: Dict[InterfaceId, InterfaceValueType] = {}
            simulation_step_request: SimulationStepRequest = message.payload(SimulationStepRequest)
            for server_inputs in simulation_step_request.inputs:
                received_inputs[server_inputs.name] = server_inputs.value
            data = self.on_simulation_step(received_inputs, self._execution_config.step_size_in_seconds())
            self._channel.send(
                ESPChannelMessageJson.answer_with_payload(
                    request_message=message,
                    payload=data,
                ),
            )

        elif message.type() == MessageType.SIMULATION_STOP:
            Client.logger.debug("Handle stop simulation")
            self.on_simulation_stop()
            self._channel.send(ESPChannelMessageJson.empty_answer(message))
            self._is_finished = True

        else:
            Client.logger.error(f"Unknown message type: '{message.type()}'")

    def on_app_shutdown(self) -> None:
        self._channel.close()

    def _init_image_renderer_connection(self) -> None:
        if self._client_config.server_config().image_renderer_port is None:
            Client.logger.debug("ImageRendererPort not set -> no image rendering will happen.")
            return
        Client.logger.debug("Initializing the image service.")
        self._image_renderer_socket = RenderingSocketClient(
            uri=f"ws://{self._client_config.server_config().server_address.ip}:{self._client_config.server_config().image_renderer_port}",
            client_config=self._client_config,
            renderer_service=self.image_renderer_service(),
        )
        started = self._image_renderer_socket.start()
        timeout = 5
        started.wait(timeout)
        if not started:
            Client.logger.warning(
                f"The image renderer connection was not established within {timeout}s -> " +
                "the simulation will execute but you may not receive any images from this client.",
            )
