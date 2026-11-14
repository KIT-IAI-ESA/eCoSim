from datetime import datetime, timedelta, timezone

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType

from tests.client.spy_simulator_client import SpySimulatorClient

_START_DATE = datetime(year=2024, month=1, day=1, tzinfo=timezone.utc)


def _payloads(restored_steps: int = 0) -> dict[MessageType, MessageData]:
    return {
        MessageType.SIMULATION_STEP: SimulationStepRequest(step=0, inputs=[]),
        MessageType.SIMULATION_STEP_BATCH: SimulationStepBatchRequest(
            start_datetime=_START_DATE,
            inputs={_START_DATE + timedelta(seconds=step + 1): [] for step in range(restored_steps)},
        ),
    }


def test_a_finished_run_counts_the_steps_of_its_model() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 3, MessageType.SIMULATION_STOP],
        payloads=_payloads(),
    )

    assert (client.completed_steps, client.restored_steps) == (3, 0)


def test_a_restore_counts_the_restored_steps_apart() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, MessageType.SIMULATION_STEP_BATCH, MessageType.SIMULATION_STEP, MessageType.SIMULATION_STOP],
        payloads=_payloads(restored_steps=2),
    )

    assert (client.completed_steps, client.restored_steps) == (1, 2)


def test_the_model_time_adds_up_the_time_inside_the_model_steps() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, MessageType.SIMULATION_STEP_BATCH, MessageType.SIMULATION_STEP, MessageType.SIMULATION_STOP],
        payloads=_payloads(restored_steps=2),
        seconds_per_model_step=1.5,
    )

    assert client.model_time_in_seconds == 4.5


def test_a_finished_run_ends_with_its_steps_and_the_time_its_model_took() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 2, MessageType.SIMULATION_STOP],
        payloads=_payloads(),
        seconds_per_model_step=1.5,
    )

    assert client.end_line() == "house#house finished after 2 steps, the model took 3.0 s in total"


def test_a_finished_restored_run_names_its_restored_steps_apart_and_one_step_in_the_singular() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, MessageType.SIMULATION_STEP_BATCH, MessageType.SIMULATION_STEP, MessageType.SIMULATION_STOP],
        payloads=_payloads(restored_steps=1),
    )

    assert client.end_line() == "house#house finished after 1 step and 1 restored step, the model took 0.00 s in total"


def test_a_run_whose_connection_ended_early_names_the_steps_it_did() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 2],
        payloads=_payloads(),
    )

    assert client.end_line() == "house#house: the connection to the server ended after 2 steps, before the simulation was finished."


def test_a_run_whose_connection_ended_before_the_start_points_to_the_server_output() -> None:
    client = SpySimulatorClient.of_ended_run(message_types=[])

    assert client.end_line() == "house#house: the connection to the server ended before the simulation started. The server output says why."
