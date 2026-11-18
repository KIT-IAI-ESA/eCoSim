import logging
from datetime import datetime, timedelta, timezone

import pytest
from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType

from tests.client.spy_simulator_client import SpySimulatorClient


def _payloads(restored_steps: int = 0) -> dict[MessageType, MessageData]:
    start_date = datetime(year=2024, month=1, day=1, tzinfo=timezone.utc)
    return {
        MessageType.SIMULATION_STEP: SimulationStepRequest(step=0, inputs=[]),
        MessageType.SIMULATION_STEP_BATCH: SimulationStepBatchRequest(
            start_datetime=start_date,
            inputs={start_date + timedelta(seconds=step + 1): [] for step in range(restored_steps)},
        ),
    }


def _end_line(caplog: pytest.LogCaptureFixture) -> str:
    return [record.getMessage() for record in caplog.records if record.getMessage().startswith("house#house")][-1]


def test_a_finished_run_counts_the_steps_of_its_model() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 3, MessageType.SIMULATION_STOP],
        payloads=_payloads(),
    )

    assert client.completed_steps == 3


def test_a_restore_counts_the_restored_steps_too() -> None:
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, MessageType.SIMULATION_STEP_BATCH, MessageType.SIMULATION_STEP, MessageType.SIMULATION_STOP],
        payloads=_payloads(restored_steps=2),
    )

    assert client.completed_steps == 3


def test_a_finished_run_ends_with_its_steps(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, MessageType.SIMULATION_STEP, MessageType.SIMULATION_STOP],
        payloads=_payloads(),
    )

    assert _end_line(caplog=caplog) == "house#house finished after 1 step."


def test_a_run_whose_connection_ended_early_shows_the_steps_it_did(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 2],
        payloads=_payloads(),
    )

    assert _end_line(caplog=caplog) == "house#house: the connection to the server ended after 2 steps, before the simulation was finished."


def test_a_run_whose_connection_ended_before_the_start_points_to_the_server_output(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[])

    assert _end_line(caplog=caplog) == "house#house: the connection to the server ended before the simulation started. The server output says why."
