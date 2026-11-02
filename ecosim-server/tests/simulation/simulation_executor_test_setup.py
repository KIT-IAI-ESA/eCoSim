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
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement
from ecosim_server.server_state import ServerState
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from ecosim_test_common.test_data.error_recording_thread import ErrorRecordingThread
from tests.data.generate_server_config import generate_server_config
from tests.simulation.history_test_setup import RecordingRepositories, values

CLIENT_ID = ClientID(model_name="model", simulator_name="simulator")
SECOND_CLIENT_ID = ClientID(model_name="second_model", simulator_name="simulator")
RUN_LIMIT_IN_SECONDS = 10.0
_START_DATE = datetime(year=2025, month=1, day=1)

MessageReaction = Callable[["FakeClient", ESPChannelMessage], None]


def answer(client: FakeClient, message: ESPChannelMessage) -> None:
    client.answered_types.append(message.type())
    client.communication.add_message_from_client(
        client_id=client.client_id,
        received_message=ESPChannelMessageJson.answer_with_payload(request_message=message, payload=ClientSimStepData(interface_values=[])),
    )


def lose_connection(client: FakeClient, _message: ESPChannelMessage) -> None:
    client.communication.set_client_connected_state(client_id=client.client_id, connected=False)


def fail_send(_client: FakeClient, _message: ESPChannelMessage) -> None:
    raise ConnectionError("broken pipe")


def answer_after(delay_in_seconds: float) -> MessageReaction:
    def reaction(client: FakeClient, message: ESPChannelMessage) -> None:
        threading.Timer(interval=delay_in_seconds, function=answer, args=(client, message)).start()

    return reaction


@dataclass
class FakeClient:
    client_id: ClientID
    communication: ClientCommunication
    reactions: dict[MessageType, MessageReaction]
    received_types: List[MessageType] = field(default_factory=list)
    answered_types: List[MessageType] = field(default_factory=list)

    def on_send(self, message: ESPChannelMessage) -> None:
        self.received_types.append(message.type())
        self.reactions.get(message.type(), answer)(self, message)


def _simulation_config(client_ids: tuple[ClientID, ...], restore: bool) -> SimulationConfig:
    return SimulationConfig(
        clients=[
            ClientSimulatorConfig(simulator_name=client_id.simulator_name, model_name=client_id.model_name, interfaces=[], client_id=client_id)
            for client_id in client_ids
        ],
        start_date=_START_DATE,
        logical_delays=[],
        pace=1.0,
        steps=1,
        step_size_in_ms=1_000,
        restore=restore,
    )


def _repositories(client_ids: tuple[ClientID, ...], restore: bool) -> RecordingRepositories:
    repositories = RecordingRepositories()
    for client_id in client_ids:
        measurements = repositories.measurement_repository(client_id)
        measurements.blocker.set()
        if restore:
            measurements.entries.append(MeasurementEntry(values=values(), timestamp=_START_DATE))
    return repositories


def executor_with_clients(
    reactions_by_client: dict[ClientID, dict[MessageType, MessageReaction]],
    restore: bool = False,
) -> tuple[SimulationExecutor, List[FakeClient]]:
    client_ids = tuple(reactions_by_client)
    simulation_config = _simulation_config(client_ids=client_ids, restore=restore)
    server_config = generate_server_config()
    communication = ClientCommunication.of(server_config=server_config, simulation_config=simulation_config)
    fake_clients = [
        FakeClient(client_id=client_id, communication=communication, reactions=reactions) for client_id, reactions in reactions_by_client.items()
    ]
    for fake_client in fake_clients:
        _connect(fake_client)
    executor = SimulationExecutor(
        simulation_config=simulation_config,
        server_config=server_config,
        server_state=MagicMock(spec=ServerState),
        repositories=_repositories(client_ids=client_ids, restore=restore),
        server_measurement=MagicMock(spec=ServerTimeMeasurement),
        client_communication=communication,
    )
    return executor, fake_clients


def executor_with_client(
    reactions: dict[MessageType, MessageReaction],
    restore: bool = False,
) -> tuple[SimulationExecutor, FakeClient]:
    executor, fake_clients = executor_with_clients(reactions_by_client={CLIENT_ID: reactions}, restore=restore)
    return executor, fake_clients[0]


def _connect(fake_client: FakeClient) -> None:
    channel = MagicMock(spec=ESPChannel)
    channel.send.side_effect = fake_client.on_send
    fake_client.communication.add_if_needed(
        client_config=ClientMetaData(version="1", simulator_name=fake_client.client_id.simulator_name, model_name=fake_client.client_id.model_name),
        connection=ClientConnection(_channel=channel, address=ConnectionAddress(ip="127.0.0.1", port=1)),
    )
    fake_client.communication.set_client_ready_for_simulation(fake_client.client_id)


def error_of_bounded_run(executor: SimulationExecutor) -> Exception | None:
    run = ErrorRecordingThread(target=partial(executor.execute, rendering_socket=None))
    run.start()
    run.assert_ends_within(limit_in_seconds=RUN_LIMIT_IN_SECONDS)
    return run.error
