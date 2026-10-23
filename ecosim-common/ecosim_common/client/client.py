from abc import abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, assert_never

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
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.data.protocol_interface_value import (
    InterfaceValueType,
    ProtocolInterfaceValue,
)
from ecosim_common.communication.data.server_interface_settings import (
    ServerInterfaceSettings,
)
from ecosim_common.communication.data.simulation_setup_message import (
    SimulationSetupMessage,
)
from ecosim_common.communication.data.simulation_step_batch_request import (
    SimulationStepBatchRequest,
)
from ecosim_common.communication.data.simulation_step_request import (
    SimulationStepRequest,
)
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.datetime.date_time_to_millis import (
    date_time_to_millis_since_unix_epoch,
)
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass
class Client(ShutdownListener):
    logger: ClassVar[ESPLogger] = ESPLogger("Client")

    _client_config: ClientConfig = field()
    _execution_config: ExecutionConfig = field(default_factory=ExecutionConfig)
    _channel_connector: ESPChannelConnector = field(init=False)
    _channel_or_none: ESPChannel | None = field(default=None)
    _image_renderer_socket: RenderingSocketClient | None = field(default=None)
    _is_finished: bool = field(default=False)
    _was_started: ParallelEvent = field(init=False)
    _image_renderer_service: SimulationRendererService | None = field(default=None)

    def __post_init__(self) -> None:
        self._client_config.print_to_info()
        self._channel_connector = ESPChannelConnector(_communication_protocol=self._client_config.communication_protocol())
        self._was_started = ParallelEvent.for_communication_protocol(self._client_config.communication_protocol())
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

    def start(self) -> None:
        if self._was_started.is_set():
            Client.logger.warning("Client already started, but 'start' called again. This should not happen in normal operation.")
        self._was_started.set()
        Client.logger.info(
            "Starting to connect to %s:%s",
            self._client_config.server_config().server_address.ip,
            self._client_config.server_config().server_address.port,
        )
        self._connect_channel()
        self._channel.listen_on_message_async(
            on_message=self._handle_message,
        )

    def was_started_event(self) -> ParallelEvent:
        return self._was_started

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
            "Connected to socket successfully: %s:%s",
            self._client_config.server_config().server_address.ip,
            self._client_config.server_config().server_address.port,
        )

    def _before_handle_message(
        self,
        message: ESPChannelMessage,
    ) -> None:
        """
        A simple callback for things, that need to be done before a message is handled.
        """
        pass

    def _handle_message(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Received and handling message")
        self._before_handle_message(message=message)
        message_type = message.type()
        match message_type:
            case MessageType.CLIENT_META_DATA_REQUEST:
                self._handle_client_meta_data_request(message)
            case MessageType.INTERFACE_REQUEST:
                self._handle_interface_requests(message)
            case MessageType.INTERFACE_SETTINGS:
                self._handle_interface_settings(message)
            case MessageType.SIMULATION_SETUP:
                self._handle_simulation_setup(message)
            case MessageType.SIMULATION_START:
                self._handle_simulation_start(message)
            case MessageType.SIMULATION_STEP:
                self._handle_simulation_step(message)
            case MessageType.SIMULATION_STEP_BATCH:
                self._handle_simulation_step_batch(message)
            case MessageType.SIMULATION_STOP:
                self._handle_simulation_stop(message)
            case MessageType.PING:
                self._handle_ping(message)
            case MessageType.UNKNOWN:
                Client.logger.error("Unknown message type: '%s'", message_type)
            case _:
                assert_never(message_type)

    def on_app_shutdown(self) -> None:
        if self._channel_or_none is None:
            Client.logger.debug("Client was never connected -> no channel to close.")
            return
        self._channel_or_none.close()

    def _init_image_renderer_connection(self) -> None:
        if self._client_config.server_config().image_renderer_port is None:
            Client.logger.debug(
                "ImageRendererPort not set -> no image rendering will happen.",
            )
            return
        Client.logger.debug("Initializing the image service.")
        image_service = self._image_renderer_service
        if image_service is None:
            Client.logger.warning("No image renderer service was initialized but image rendering was requested. No images will be rendered.")
            return

        self._image_renderer_socket = RenderingSocketClient(
            uri=f"ws://{self._client_config.server_config().server_address.ip}:{self._client_config.server_config().image_renderer_port}",
            client_config=self._client_config,
            renderer_service=image_service,
        )
        started = self._image_renderer_socket.start()
        timeout = 5
        started.wait(timeout)
        if not started:
            Client.logger.warning(
                "The image renderer connection was not established within %ss -> the simulation will execute "
                "but you may not receive any images from this client.",
                timeout,
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
        config_validated = self._client_config.interfaces_config().validate_config_with_server(
            server_interface_settings,
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
        Client.logger.debug("  -> step size (in seconds): %s", self._execution_config.step_size_in_seconds())
        Client.logger.debug("_handle_simulation_setup: Attempting to send back")
        self._channel.send(ESPChannelMessageJson.empty_answer(message))

    def _handle_simulation_start(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handling start simulation")
        data: ClientSimStepData = self.on_simulation_start()
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
        last_timestamp = date_time_to_millis_since_unix_epoch(
            simulation_step_batch_request.start_datetime,
        )
        input_interfaces = self._client_config.interfaces_config().input_interface_names()
        required_input_interfaces = self._client_config.interfaces_config().input_interface_names(
            only_required=True,
        )
        last_simulation_step_data: ClientSimStepData | None = None
        for step_datetime, inputs in sorted(
            simulation_step_batch_request.inputs.items(),
        ):
            Client.logger.debug("Executing batch step %s", step_datetime)
            filtered_inputs = [input for input in inputs if input.name in input_interfaces]
            filtered_interface_names = [interface.name for interface in filtered_inputs]
            for required_input in required_input_interfaces:
                if required_input not in filtered_interface_names:
                    error_message = f"Missing input interface '{required_input}' in batch step {step_datetime} - cannot restore state."
                    Client.logger.error(error_message)
                    raise RuntimeError(error_message)
            values = self._protocol_interface_value_to_dict(filtered_inputs)
            current_timestamp = date_time_to_millis_since_unix_epoch(step_datetime)
            last_simulation_step_data = self.on_simulation_step(
                values,
                (current_timestamp - last_timestamp) / 1000,
            )
            last_timestamp = current_timestamp
            for new_interface_value in last_simulation_step_data.interface_values:
                matching_interface = next(
                    (interface for interface in inputs if interface.name == new_interface_value.name),
                    None,
                )
                if matching_interface is None:
                    Client.logger.warning("Batch step %s: No matching interface found for interface '%s'", step_datetime, new_interface_value.name)
                    continue
                if matching_interface.value == new_interface_value.value:
                    Client.logger.debug("Batch step %s: Value matched for interface '%s'", step_datetime, new_interface_value.name)
                else:
                    Client.logger.error(
                        "Batch step %s: Value mismatch for interface '%s': expected=%s, actual=%s",
                        step_datetime,
                        new_interface_value.name,
                        matching_interface.value,
                        new_interface_value.value,
                    )

        if last_simulation_step_data is None:
            error_message = "No simulation step was executed."
            Client.logger.error(error_message)
            raise RuntimeError(error_message)
        self._channel.send(
            ESPChannelMessageJson.answer_with_payload(
                request_message=message,
                payload=last_simulation_step_data,
            ),
        )

    def _handle_simulation_stop(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handle stop simulation")
        self.on_simulation_stop()
        self._channel.send(ESPChannelMessageJson.empty_answer(message))
        self._is_finished = True

    def _handle_ping(
        self,
        message: ESPChannelMessage,
    ) -> None:
        Client.logger.debug("Handle ping")
        self._channel.send(ESPChannelMessageJson.empty_answer(message))
