import logging

import pytest
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.communication.data.simulation_setup_message import SimulationSetupMessage
from ecosim_common.communication.message_type import MessageType
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
