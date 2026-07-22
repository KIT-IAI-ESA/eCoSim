from cloudpickle import cloudpickle
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_server.config.server_config import DatabaseConfig, MainConfig, ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.message_buffer import BufferedClientMessage, OnMessageCallbackHandler
from ecosim_server.simulation.current_step_data import CurrentStepData
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from integration_tests.tech.resource_utils import resource_path_file


def test_pickle_handle_sim_step_message() -> None:
    handler = OnMessageCallbackHandler.for_communication_protocol(
        protocol=CommunicationProtocol.DASK,
        client_ids=(),
        message_types=(),
        callback=lambda message: SimulationExecutor._handle_received_sim_step(  # noqa: SLF001
            current_step=1,
            current_step_data=CurrentStepData(
                simulation_config=SimulationConfig.of_config_file_and_params(
                    resource_path_file("simulation.json"),
                    steps=1,
                ),
                server_config=ServerConfig(
                    server=MainConfig(
                        host="localhost",
                        port=8080,
                        communication_protocol=CommunicationProtocol.DASK,
                    ),
                    database=DatabaseConfig(
                        host="localhost",
                        port=5432,
                        ssl=False,
                        drop_existing_schema=False,
                        username="test",
                        password="",
                        schema="",
                    ),
                ),
            ),
            received_message=BufferedClientMessage(
                client_id=ClientID(model_name="", simulator_name=""),
                message=ESPChannelMessageJson(
                    _type=MessageType.SIMULATION_STEP,
                    _correlation_id=CorrelationId.default_id(),
                    _payload=b"",
                ),
            ),
            all_clients_handled_event=ParallelEvent.for_communication_protocol(CommunicationProtocol.DASK),
            handled_clients={},
            ready_for_execution_data_by_clients={},
        ),  # noqa: SLF001
    )
    cloudpickle.dumps(handler)
