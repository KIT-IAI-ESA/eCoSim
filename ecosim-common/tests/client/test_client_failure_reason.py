import pytest
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.communication.data.simulation_setup_message import SimulationSetupMessage
from ecosim_common.communication.data.simulation_step_request import SimulationStepRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.shutdown_manager import ShutdownManager

from tests.client.spy_simulator_client import SpySimulatorClient


def test_a_model_that_cannot_run_the_simulation_config_is_never_started_and_the_client_says_why(caplog: pytest.LogCaptureFixture) -> None:
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
    assert "The FMU house.fmu has no input T_outdoor. This client does not start the simulation." in caplog.messages
    assert "house#house did not start the simulation. The error above says why." in caplog.messages


def test_a_client_rejected_after_its_names_is_pointed_to_simulator_name_and_model_name(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(
        message_types=[MessageType.CLIENT_META_DATA_REQUEST],
        client_id=ClientID(model_name="house", simulator_name="hous"),
    )

    end_line = (
        "house#hous: the server rejected simulator name 'hous' and model name 'house'. "
        + "The simulation config has no simulator with these names or another client already uses them. "
        + "Check simulator_name and model_name in the [simulator] section of the client config."
    )
    assert end_line in caplog.messages


def test_a_client_rejected_after_its_interfaces_is_pointed_to_a_required_interface(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.CLIENT_META_DATA_REQUEST, MessageType.INTERFACE_REQUEST])

    required_interface = "The simulation config marks an interface as required that the .fmc file does not list."
    assert any(required_interface in message for message in caplog.messages)


def test_a_model_that_fails_at_the_start_is_reported_with_its_error(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START], initialize_fails=True)

    assert "house#house: the model failed at the start of the simulation: RuntimeError: initialize failed" in caplog.messages
    assert "house#house failed at the start of the simulation. The error above says why." in caplog.messages


def test_a_model_that_fails_in_its_second_step_is_reported_with_step_1_and_its_error(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(
        message_types=[MessageType.SIMULATION_START, *[MessageType.SIMULATION_STEP] * 3],
        payloads={MessageType.SIMULATION_STEP: SimulationStepRequest(step=0, inputs=[])},
        failing_step=1,
    )

    assert "house#house: the model failed in step 1: RuntimeError: step failed" in caplog.messages
    assert "house#house failed in step 1. The error above says why." in caplog.messages


def test_a_server_that_closes_after_the_start_says_the_run_ended_at_the_start(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START])

    end_line = "house#house: the connection to the server ended at the start of the simulation, before the first step. The server output says why."
    assert end_line in caplog.messages


def test_a_ping_after_the_start_does_not_hide_that_the_run_ended_at_the_start(caplog: pytest.LogCaptureFixture) -> None:
    SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START, MessageType.PING])

    assert any("ended at the start of the simulation" in message for message in caplog.messages)
