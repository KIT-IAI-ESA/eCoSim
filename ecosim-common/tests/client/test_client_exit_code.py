from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.shutdown_manager import ShutdownManager

from tests.client.spy_simulator_client import SpySimulatorClient


def test_a_run_the_server_stops_ends_with_the_success_exit_code() -> None:
    client = SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_STOP])

    assert client.exit_code() == ShutdownManager.SUCCESS_EXIT_CODE


def test_a_server_closing_mid_run_ends_with_the_failed_run_exit_code() -> None:
    client = SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START])

    assert client.exit_code() == ShutdownManager.FAILED_RUN_EXIT_CODE


def test_a_raising_handler_ends_the_run_with_the_failed_run_exit_code() -> None:
    client = SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_START, MessageType.SIMULATION_STOP], initialize_fails=True)

    assert client.exit_code() == ShutdownManager.FAILED_RUN_EXIT_CODE


def test_a_raising_stop_handler_ends_the_run_with_the_failed_run_exit_code() -> None:
    client = SpySimulatorClient.of_ended_run(message_types=[MessageType.SIMULATION_STOP], stop_fails=True)

    assert client.exit_code() == ShutdownManager.FAILED_RUN_EXIT_CODE
