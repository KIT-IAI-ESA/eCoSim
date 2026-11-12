from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Callable, List
from unittest.mock import MagicMock

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement
from ecosim_server.server_state import ServerState
from ecosim_server.simulation.response_timeouts import ResponseTimeouts
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from ecosim_test_common.test_data.error_recording_thread import ErrorRecordingThread
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from tests.data.generate_postgres_name_config import generate_client_simulator_config
from tests.data.generate_server_config import generate_server_config
from tests.simulation.history_test_setup import RecordingRepositories, values

CLIENT_ID = ClientID(model_name="model", simulator_name="simulator")
_START_DATE = datetime(year=2025, month=1, day=1)

MessageReaction = Callable[["FakeClient", ESPChannelMessage], None]


def answer(client: FakeClient, message: ESPChannelMessage) -> None:
    client.communication.add_message_from_client(
        client_id=client.client_id,
        received_message=ESPChannelMessageJson.answer_with_payload(request_message=message, payload=ClientSimStepData(interface_values=[])),
    )


def lose_connection(client: FakeClient, _message: ESPChannelMessage) -> None:
    client.communication.set_client_connected_state(client_id=client.client_id, connected=False)


def answer_after(delay_in_seconds: float) -> MessageReaction:
    def reaction(client: FakeClient, message: ESPChannelMessage) -> None:
        threading.Timer(interval=delay_in_seconds, function=answer, args=(client, message)).start()

    return reaction


@dataclass
class FakeClient:
    client_id: ClientID
    communication: ClientCommunication
    reactions: dict[MessageType, MessageReaction]
    received_messages: List[ESPChannelMessage] = field(default_factory=list)

    def connect(self) -> None:
        channel = MagicMock(spec=ESPChannel)
        channel.send.side_effect = self.on_send
        self.communication.add_if_needed(
            client_config=ClientMetaData(version="1", simulator_name=self.client_id.simulator_name, model_name=self.client_id.model_name),
            connection=ClientConnection(_channel=channel, address=ConnectionAddress(ip="127.0.0.1", port=1)),
        )
        self.communication.set_client_ready_for_simulation(client_id=self.client_id)

    def on_send(self, message: ESPChannelMessage) -> None:
        self.received_messages.append(message)
        self.reactions.get(message.type(), answer)(self, message)

    def received_steps(self) -> List[int]:
        return [message.correlation_id().to_int() for message in self.received_messages if message.type() == MessageType.SIMULATION_STEP]

    def received_inputs(self, interface: InterfaceId) -> List[InterfaceValue]:
        return [
            interface_value.value
            for message in self.received_messages
            if message.type() == MessageType.SIMULATION_STEP
            for interface_value in message.payload(SimulationStepRequest).inputs
            if interface_value.name == interface
        ]


def _simulation_config(client_ids: tuple[ClientID, ...], restore: bool) -> SimulationConfig:
    return SimulationConfig(
        clients=[
            generate_client_simulator_config(simulator_name=client_id.simulator_name, model_name=client_id.model_name) for client_id in client_ids
        ],
        start_date=_START_DATE,
        logical_delays=[],
        pace=1.0,
        steps=2,
        step_size_in_ms=1_000,
        restore=restore,
    )


def _repositories(simulation_config: SimulationConfig) -> RecordingRepositories:
    repositories = RecordingRepositories()
    for client_id in simulation_config.client_ids():
        measurements = repositories.measurement_repository(client_id)
        measurements.blocker.set()
        if simulation_config.restore:
            # step -1 holds the default values
            measurements.entries.extend(MeasurementEntry(values=values(), timestamp=simulation_config.date_time_for_step(step)) for step in (-1, 0))
    return repositories


def executor_with_clients(
    reactions_by_client: dict[ClientID, dict[MessageType, MessageReaction]],
    restore: bool = False,
    response_timeouts: ResponseTimeouts = ResponseTimeouts(),
) -> tuple[SimulationExecutor, List[FakeClient]]:
    return executor_for_simulation_config(
        simulation_config=_simulation_config(client_ids=tuple(reactions_by_client), restore=restore),
        reactions_by_client=reactions_by_client,
        response_timeouts=response_timeouts,
    )


def executor_for_simulation_config(
    simulation_config: SimulationConfig,
    reactions_by_client: dict[ClientID, dict[MessageType, MessageReaction]],
    response_timeouts: ResponseTimeouts = ResponseTimeouts(),
) -> tuple[SimulationExecutor, List[FakeClient]]:
    server_config = generate_server_config()
    communication = ClientCommunication.of(server_config=server_config, simulation_config=simulation_config)
    fake_clients = [
        FakeClient(client_id=client_id, communication=communication, reactions=reactions) for client_id, reactions in reactions_by_client.items()
    ]
    for fake_client in fake_clients:
        fake_client.connect()
    executor = SimulationExecutor(
        simulation_config=simulation_config,
        server_config=server_config,
        server_state=MagicMock(spec=ServerState),
        repositories=_repositories(simulation_config),
        server_measurement=MagicMock(spec=ServerTimeMeasurement),
        client_communication=communication,
        response_timeouts=response_timeouts,
    )
    return executor, fake_clients


def executor_with_client(
    reactions: dict[MessageType, MessageReaction],
    restore: bool = False,
    response_timeouts: ResponseTimeouts = ResponseTimeouts(),
) -> tuple[SimulationExecutor, FakeClient]:
    executor, fake_clients = executor_with_clients(reactions_by_client={CLIENT_ID: reactions}, restore=restore, response_timeouts=response_timeouts)
    return executor, fake_clients[0]


def error_of_bounded_run(executor: SimulationExecutor) -> Exception | None:
    run = ErrorRecordingThread(target=partial(executor.execute, rendering_socket=None))
    run.start()
    run.assert_ends_within(timeout_in_seconds=WAIT_TIMEOUT_IN_SECONDS)
    return run.error
