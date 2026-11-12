from __future__ import annotations

from pathlib import Path
from typing import Callable

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue, ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_server.config.simulation_config import SimulationConfig
from tests.simulation.simulation_executor_test_setup import FakeClient, MessageReaction, error_of_bounded_run, executor_for_simulation_config

StepOutputs = Callable[[int], dict[InterfaceId, InterfaceValue]]


def answer_with(outputs_for_step: StepOutputs) -> MessageReaction:
    def reaction(client: FakeClient, message: ESPChannelMessage) -> None:
        outputs = outputs_for_step(message.payload(SimulationStepRequest).step)
        client.communication.add_message_from_client(
            client_id=client.client_id,
            received_message=ESPChannelMessageJson.answer_with_payload(
                request_message=message,
                payload=ClientSimStepData(interface_values=[ProtocolInterfaceValue(name=name, value=value) for name, value in outputs.items()]),
            ),
        )

    return reaction


def run_simulation(
    simulation_file: Path,
    steps: int,
    outputs_by_simulator: dict[str, StepOutputs],
) -> dict[str, FakeClient]:
    simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=simulation_file, steps=steps)
    executor, fake_clients = executor_for_simulation_config(
        simulation_config=simulation_config,
        reactions_by_client={
            client_id: {MessageType.SIMULATION_STEP: answer_with(outputs_by_simulator.get(client_id.simulator_name, lambda _step: {}))}
            for client_id in simulation_config.client_ids()
        },
    )
    assert error_of_bounded_run(executor) is None
    return {fake_client.client_id.simulator_name: fake_client for fake_client in fake_clients}
