import multiprocessing
import os
import signal
import time
from datetime import datetime

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from integration_tests.test_data.server_client.lost_client_setup import (
    HEALTHY,
    LOST,
    RUN_LIMIT_IN_SECONDS,
    Inputs,
    assert_failed_naming_the_lost_client,
    assert_run_ended,
    crash,
    lost_client_server,
    new_client,
    start_server,
)
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient


@pytest.fixture(autouse=True)
def _short_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("_STEP_RESPONSE_TIMEOUT_IN_SECONDS", "_START_RESPONSE_TIMEOUT_IN_SECONDS", "_RESTORE_CONNECTION_CHECK_INTERVAL_IN_SECONDS"):
        monkeypatch.setattr(SimulationExecutor, name, 1)


def _answer_slowly(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    time.sleep(1.5)
    return ClientSimStepData(interface_values=[])


def _crash_in_step(client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    crash(client)


def _kill_own_process(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    os.kill(os.getpid(), signal.SIGKILL)
    raise SystemExit


class _ClientCrashingAtStart(SimpleTestClient):
    def on_simulation_start(self) -> ClientSimStepData:
        crash(self)


def _run_client_killing_its_process(port: int) -> None:
    client = new_client(protocol=CommunicationProtocol.TCP_SOCKET, port=port, client_id=LOST, on_step=_kill_own_process)
    client.start()
    client.wait_until_finished()


def test_client_lost_mid_step_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    thread, errors = start_server(lost_client_server(protocol=communication_protocol, port=port))
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, on_step=_crash_in_step).start()

    assert_failed_naming_the_lost_client(thread=thread, errors=errors)


def test_killed_client_process_mid_step_fails_the_run() -> None:
    port = get_free_port()
    thread, errors = start_server(lost_client_server(protocol=CommunicationProtocol.TCP_SOCKET, port=port))
    new_client(protocol=CommunicationProtocol.TCP_SOCKET, port=port, client_id=HEALTHY).start()
    process = multiprocessing.get_context("spawn").Process(target=_run_client_killing_its_process, args=(port,), daemon=True)
    process.start()
    try:
        assert_failed_naming_the_lost_client(thread=thread, errors=errors)
        process.join(RUN_LIMIT_IN_SECONDS)
        assert process.exitcode == -signal.SIGKILL
    finally:
        process.kill()
        process.join(RUN_LIMIT_IN_SECONDS)


def test_client_lost_during_start_up_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    thread, errors = start_server(lost_client_server(protocol=communication_protocol, port=port))
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, client_type=_ClientCrashingAtStart).start()

    assert_failed_naming_the_lost_client(thread=thread, errors=errors)


def test_client_lost_during_restore_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server = lost_client_server(protocol=communication_protocol, port=port, restore=True)
    for client_id in (HEALTHY, LOST):
        server.measurement_repository(client_id=client_id).add(
            values=(ProtocolInterfaceValue(name="value", value=1.0),),
            timestamp=datetime(year=2025, month=1, day=1),
        )
    thread, errors = start_server(server)
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, on_step=_crash_in_step).start()

    assert_failed_naming_the_lost_client(thread=thread, errors=errors)


def test_slow_client_does_not_fail_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    thread, errors = start_server(lost_client_server(protocol=communication_protocol, port=port))
    new_client(protocol=communication_protocol, port=port, client_id=HEALTHY).start()
    new_client(protocol=communication_protocol, port=port, client_id=LOST, on_step=_answer_slowly).start()

    assert_run_ended(thread)
    assert errors == []
