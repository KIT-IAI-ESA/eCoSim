import multiprocessing
import signal
from datetime import datetime

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from integration_tests.test_data.server_client.lost_client_setup import (
    HEALTHY,
    LOST,
    RUN_LIMIT_IN_SECONDS,
    SHORT_TIMEOUT_IN_SECONDS,
    SLOW,
    answer_slowly,
    assert_failed_naming_the_lost_client,
    crash,
    crash_in_step,
    new_client,
    run_client_killing_its_process,
    start_server,
    two_client_server,
)


@pytest.fixture(autouse=True)
def _short_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("_STEP_RESPONSE_TIMEOUT_IN_SECONDS", "_START_RESPONSE_TIMEOUT_IN_SECONDS", "_RESTORE_CONNECTION_CHECK_INTERVAL_IN_SECONDS"):
        monkeypatch.setattr(SimulationExecutor, name, SHORT_TIMEOUT_IN_SECONDS)


def test_client_lost_mid_step_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server_run = start_server(two_client_server(protocol=communication_protocol, port=port, second_client_id=LOST))
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, on_step=crash_in_step).start()

    assert_failed_naming_the_lost_client(server_run=server_run, waiting_for="response of step")


def test_killed_client_process_mid_step_fails_the_run() -> None:
    port = get_free_port()
    server_run = start_server(two_client_server(protocol=CommunicationProtocol.TCP_SOCKET, port=port, second_client_id=LOST))
    new_client(protocol=CommunicationProtocol.TCP_SOCKET, port=port, client_id=HEALTHY).start()
    process = multiprocessing.get_context("spawn").Process(target=run_client_killing_its_process, args=(port,), daemon=True)
    process.start()
    try:
        assert_failed_naming_the_lost_client(server_run=server_run, waiting_for="response of step")
        process.join(RUN_LIMIT_IN_SECONDS)
        assert process.exitcode == -signal.SIGKILL
    finally:
        process.kill()
        process.join(RUN_LIMIT_IN_SECONDS)


def test_client_lost_during_start_up_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server_run = start_server(two_client_server(protocol=communication_protocol, port=port, second_client_id=LOST))
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, on_start=crash).start()

    assert_failed_naming_the_lost_client(server_run=server_run, waiting_for="start their simulation")


def test_client_lost_during_restore_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server = two_client_server(protocol=communication_protocol, port=port, second_client_id=LOST, restore=True)
    for client_id in (HEALTHY, LOST):
        server.measurement_repository(client_id=client_id).add(
            values=(ProtocolInterfaceValue(name="value", value=1.0),),
            timestamp=datetime(year=2025, month=1, day=1),
        )
    server_run = start_server(server)
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, on_step=crash_in_step).start()

    assert_failed_naming_the_lost_client(server_run=server_run, waiting_for="restore response")


def test_slow_client_does_not_fail_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server_run = start_server(two_client_server(protocol=communication_protocol, port=port, second_client_id=SLOW))
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=SLOW, on_step=answer_slowly).start()

    server_run.assert_ends_within(limit_in_seconds=RUN_LIMIT_IN_SECONDS)
    assert server_run.error is None
