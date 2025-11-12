from abc import abstractmethod
from typing import Dict, List

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.client.renderer.rendering_socket_client import RenderingSocketClient
from ecosim_common.client.renderer.simulation_renderer_service import (
    SimulationRendererService,
)
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_connector import (
    ESPChannelConnector,
)
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import (
    ESPChannelMessageJson,
)
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import (
    InterfaceValueType,
    ProtocolInterfaceValue,
)
from ecosim_common.communication.data.simulation_step_batch_request import (
    SimulationStepBatchRequest,
)
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.data.simulation_step_request import (
    SimulationStepRequest,
)
from ecosim_common.communication.socket.socket_connector import SocketConnector
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.data.server_interface_settings import (
    ServerInterfaceSettings,
)
from ecosim_common.communication.data.simulation_setup_message import (
    SimulationSetupMessage,
)
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
            "Starting to connect to "
            + f"{self._client_config.server_config().server_address.ip}:{self._client_config.server_config().server_address.port}",
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
        Client.logger.info(
            f"Connected to socket successfully: "
            f"{self._client_config.server_config().server_address.ip}:{self._client_config.server_config().server_address.port}",
        )

    def _handle_message(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Received and handling message")
        if message.type() == MessageType.CLIENT_META_DATA_REQUEST:
            self._handle_client_meta_data_request(message)
        elif message.type() == MessageType.INTERFACE_REQUEST:
            self._handle_interface_requests(message)
        elif message.type() == MessageType.INTERFACE_SETTINGS:
            self._handle_interface_settings(message)
        elif message.type() == MessageType.SIMULATION_SETUP:
            self._handle_simulation_setup(message)
        elif message.type() == MessageType.SIMULATION_START:
            self._handle_simulation_start(message)
        elif message.type() == MessageType.SIMULATION_STEP:
            self._handle_simulation_step(message)
        elif message.type() == MessageType.SIMULATION_STEP_BATCH:
            self._handle_simulation_step_batch(message)
        elif message.type() == MessageType.SIMULATION_STOP:
            self._handle_simulation_stop(message)
        else:
            Client.logger.error(f"Unknown message type: '{message.type()}'")

    def on_app_shutdown(self) -> None:
        self._channel.close()

    def _init_image_renderer_connection(self) -> None:
        if self._client_config.server_config().image_renderer_port is None:
            Client.logger.debug(
                "ImageRendererPort not set -> no image rendering will happen.",
            )
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
                f"The image renderer connection was not established within {timeout}s -> "
                + "the simulation will execute but you may not receive any images from this client.",
            )

    def _handle_client_meta_data_request(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handling poss config request")
        self._channel.send(
            ESPChannelMessageJson.answer_with_payload(
                request_message=message,
                payload=self._client_config.meta_data(),
            ),
        )

    def _handle_interface_requests(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handling interface request")
        self._channel.send(
            ESPChannelMessageJson.answer_with_payload(
                request_message=message,
                payload=ModelInterfaceIds.of_interface_config(self._client_config),
            ),
        )

    def _handle_interface_settings(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handling interface settings")
        server_interface_settings: ServerInterfaceSettings = message.payload(
            ServerInterfaceSettings,
        )

        # check if config matches actual interfaces
        config_validated = (
            self._client_config.interfaces_config().validate_config_with_server(
                server_interface_settings,
            )
        )
        self._execution_config.set_server_interface_settings(server_interface_settings)

        error_occurred = not config_validated
        if error_occurred:
            Client.logger.error(
                "   ->> Could not validate the incoming input/output interfaces - there seems to be a mismatch "
                "between the client interfaces and the interfaces the server requires",
            )

        self._channel.send(ESPChannelMessageJson.empty_answer(message))

    def _handle_simulation_setup(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handling simulation setup")
        self._execution_config.set_step_size_in_ms(
            message.payload(SimulationSetupMessage).step_size_in_ms,
        )
        Client.logger.debug(
            f"  -> step size (in seconds): {self._execution_config.step_size_in_seconds()}",
        )
        self._channel.send(ESPChannelMessageJson.empty_answer(message))

    def _handle_simulation_start(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handling start simulation")
        data = self.on_simulation_start()
        self._channel.send(
            ESPChannelMessageJson.answer_with_payload(
                request_message=message,
                payload=data,
            ),
        )
        self._init_image_renderer_connection()

    def _handle_simulation_step(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.info("Handling simulation step")
        simulation_step_request: SimulationStepRequest = message.payload(
            SimulationStepRequest,
        )
        received_inputs = self._protocol_interface_value_to_dict(
            simulation_step_request.inputs,
        )
        data = self.on_simulation_step(
            received_inputs,
            self._execution_config.step_size_in_seconds(),
        )
        self._channel.send(
            ESPChannelMessageJson.answer_with_payload(
                request_message=message,
                payload=data,
            ),
        )

    def _protocol_interface_value_to_dict(
        self,
        values: List[ProtocolInterfaceValue],
    ) -> dict[InterfaceId, InterfaceValueType]:
        transformed: Dict[InterfaceId, InterfaceValueType] = {}
        for server_inputs in values:
            transformed[server_inputs.name] = server_inputs.value
        return transformed

    def _handle_simulation_step_batch(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.info("Handling simulation step batch")
        simulation_step_batch_request: SimulationStepBatchRequest = message.payload(
            SimulationStepBatchRequest,
        )

        # TODO SORT THE INPUTS!
        for i, inputs in enumerate(simulation_step_batch_request.inputs.values()):
            Client.logger.debug(f"Executing batch step {i}")
            values = self._protocol_interface_value_to_dict(inputs)
            client_step_data = self.on_simulation_step(
                values,
                simulation_step_batch_request.step_size_ms / 1000,
            )
            for interface_value in client_step_data.interface_values:
                matching_input = next(
                    (inp for inp in inputs if inp.name == interface_value.name),
                    None,
                )
                if matching_input is None:
                    Client.logger.error(
                        f"Batch step {i}: No matching input found for interface '{interface_value.name}'",
                    )
                    continue
                if matching_input.value == interface_value.value:
                    Client.logger.debug(
                        f"Batch step {i}: Value matched for interface '{interface_value.name}'",
                    )
                else:
                    Client.logger.error(
                        f"Batch step {i}: Value mismatch for interface '{interface_value.name}': "
                        f"input={matching_input.value}, output={interface_value.value}",
                    )

    def _handle_simulation_stop(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handle stop simulation")
        self.on_simulation_stop()
        self._channel.send(ESPChannelMessageJson.empty_answer(message))
        self._is_finished = True
