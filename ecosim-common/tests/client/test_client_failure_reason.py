import logging

import pytest
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.communication.data.simulation_setup_message import SimulationSetupMessage
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.shutdown_manager import ShutdownManager

from tests.client.spy_simulator_client import SpySimulatorClient


def _client_records(caplog: pytest.LogCaptureFixture) -> list[tuple[str, str]]:
    return [(record.levelname, record.getMessage()) for record in caplog.records if record.name == "Client"]


def _log_without_debug(caplog: pytest.LogCaptureFixture) -> None:
    # with debug logging, an error also shows where it was logged
    caplog.set_level(logging.INFO, logger="Client")


def test_a_model_that_cannot_run_the_simulation_config_is_never_started(caplog: pytest.LogCaptureFixture) -> None:
    _log_without_debug(caplog)
    client = SpySimulatorClient.of_ended_run(
        message_types=[MessageType.INTERFACE_SETTINGS, MessageType.SIMULATION_SETUP, MessageType.SIMULATION_START],
        payloads={
            MessageType.INTERFACE_SETTINGS: ServerInterfaceSettings(inputs=["T_outdoor"], outputs=[]),
            MessageType.SIMULATION_SETUP: SimulationSetupMessage(step_size_in_ms=1000),
        },
        model_problem="The FMU house.fmu has no input T_outdoor.",
    )

    assert client.calls == []
    assert client.exit_code() == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert ("ERROR", "The FMU house.fmu has no input T_outdoor. This client does not start the simulation.") in _client_records(caplog)
    assert ("ERROR", "house#house did not start the simulation. The error above says why.") in _client_records(caplog)


def test_a_server_that_closes_after_the_names_points_to_simulator_name_and_model_name(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(
        message_types=[MessageType.CLIENT_META_DATA_REQUEST],
        client_id=ClientID(model_name="house", simulator_name="hous"),
    )

    end_line = (
        "house#hous: the server closed the connection after this client sent simulator name 'hous' and model name 'house'. "
        + "The simulation config has no simulator with these names, or another client already uses them. "
        + "Check simulator_name and model_name in the [simulator] section of the client config."
    )
    assert ("ERROR", end_line) in _client_records(caplog)


def test_a_server_that_closes_after_the_interfaces_points_to_a_required_interface(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.CLIENT_META_DATA_REQUEST, MessageType.INTERFACE_REQUEST])

    required_interface = "The simulation config marks an interface as required that the .fmc file does not list."
    assert any(required_interface in message for _, message in _client_records(caplog))


def test_a_model_that_fails_at_the_start_is_named_in_the_end_line(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START], initialize_fails=True)

    assert ("ERROR", "house#house: the model failed at the start of the simulation. The error above says why.") in _client_records(caplog)


def test_a_model_that_fails_at_the_start_logs_its_error_with_the_client(caplog: pytest.LogCaptureFixture) -> None:
    _log_without_debug(caplog)
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START], initialize_fails=True)

    assert ("ERROR", "house#house: the model failed at the start of the simulation: RuntimeError: initialize failed") in _client_records(caplog)


def _run_whose_model_fails_in_the_second_step() -> SpySimulatorClient:
    return SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 3],
        payloads={MessageType.SIMULATION_STEP: SimulationStepRequest(step=0, inputs=[])},
        failing_step=1,
    )


def test_a_model_that_fails_in_a_step_is_named_with_the_step_counted_from_0(caplog: pytest.LogCaptureFixture) -> None:
    _run_whose_model_fails_in_the_second_step()

    # the server names the first step 0, so the second step is step 1
    assert ("ERROR", "house#house: the model failed in step 1. The error above says why.") in _client_records(caplog)


def test_a_model_that_fails_in_a_step_logs_its_error_with_the_client_and_the_step(caplog: pytest.LogCaptureFixture) -> None:
    _log_without_debug(caplog)
    _run_whose_model_fails_in_the_second_step()

    assert ("ERROR", "house#house: the model failed in step 1: RuntimeError: step failed") in _client_records(caplog)


def test_a_server_that_closes_after_the_start_says_the_run_ended_at_the_start(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START])

    end_line = "house#house: the connection to the server ended at the start of the simulation, before the first step. The server output says why."
    assert ("ERROR", end_line) in _client_records(caplog)


def test_a_ping_after_the_start_does_not_hide_that_the_run_ended_at_the_start(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START, MessageType.PING])

    assert any("ended at the start of the simulation" in message for _, message in _client_records(caplog))
