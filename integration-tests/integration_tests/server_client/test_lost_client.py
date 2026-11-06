import multiprocessing
import signal
from datetime import datetime

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.port_utils import get_free_port
from integration_tests.test_data.server_client.lost_client_setup import (
    HEALTHY,
    HOST,
    LOST,
    RUN_LIMIT_IN_SECONDS,
    SHORT_RESPONSE_TIMEOUTS,
    STEPS,
    answer_slowly,
    assert_naming_the_lost_client,
    crash,
    crash_in_step,
    run_client_killing_its_process,
)
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer


def test_client_lost_mid_step_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server_run = SimpleTestServer.for_client_ids(
        communication_protocol=communication_protocol,
        host=HOST,
        port=port,
        client_ids=(HEALTHY, LOST),
        steps=STEPS,
        response_timeouts=SHORT_RESPONSE_TIMEOUTS,
    ).start_with_error_recording()
    SimpleTestClient.of_client_id(communication_protocol=communication_protocol, server_host=HOST, server_port=port, client_id=HEALTHY).start()
    SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=LOST,
        on_simulation_step_return=crash_in_step,
    ).start()

    assert_naming_the_lost_client(server_run=server_run, limit_in_seconds=RUN_LIMIT_IN_SECONDS, waiting_for="response of step")


def test_killed_client_process_mid_step_fails_the_run() -> None:
    port = get_free_port()
    server_run = SimpleTestServer.for_client_ids(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        host=HOST,
        port=port,
        client_ids=(HEALTHY, LOST),
        steps=STEPS,
        response_timeouts=SHORT_RESPONSE_TIMEOUTS,
    ).start_with_error_recording()
    SimpleTestClient.of_client_id(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        server_host=HOST,
        server_port=port,
        client_id=HEALTHY,
    ).start()
    process = multiprocessing.get_context("spawn").Process(target=run_client_killing_its_process, args=(port,), daemon=True)
    process.start()
    try:
        assert_naming_the_lost_client(server_run=server_run, limit_in_seconds=RUN_LIMIT_IN_SECONDS, waiting_for="response of step")
        process.join(RUN_LIMIT_IN_SECONDS)
        assert process.exitcode == -signal.SIGKILL
    finally:
        process.kill()
        process.join(RUN_LIMIT_IN_SECONDS)


def test_client_lost_during_start_up_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server_run = SimpleTestServer.for_client_ids(
        communication_protocol=communication_protocol,
        host=HOST,
        port=port,
        client_ids=(HEALTHY, LOST),
        steps=STEPS,
        response_timeouts=SHORT_RESPONSE_TIMEOUTS,
    ).start_with_error_recording()
    SimpleTestClient.of_client_id(communication_protocol=communication_protocol, server_host=HOST, server_port=port, client_id=HEALTHY).start()
    SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=LOST,
        on_simulation_start_return=crash,
    ).start()

    assert_naming_the_lost_client(server_run=server_run, limit_in_seconds=RUN_LIMIT_IN_SECONDS, waiting_for="start their simulation")


def test_client_lost_during_restore_fails_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    server = SimpleTestServer.for_client_ids(
        communication_protocol=communication_protocol,
        host=HOST,
        port=port,
        client_ids=(HEALTHY, LOST),
        steps=STEPS,
        restore_simulation_run=True,
        response_timeouts=SHORT_RESPONSE_TIMEOUTS,
    )
    for client_id in (HEALTHY, LOST):
        server.measurement_repository(client_id=client_id).add(
            values=(ProtocolInterfaceValue(name="value", value=1.0),),
            timestamp=datetime(year=2025, month=1, day=1),
        )
    server_run = server.start_with_error_recording()
    SimpleTestClient.of_client_id(communication_protocol=communication_protocol, server_host=HOST, server_port=port, client_id=HEALTHY).start()
    SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=LOST,
        on_simulation_step_return=crash_in_step,
    ).start()

    assert_naming_the_lost_client(server_run=server_run, limit_in_seconds=RUN_LIMIT_IN_SECONDS, waiting_for="restore response")


def test_slow_client_does_not_fail_the_run(communication_protocol: CommunicationProtocol) -> None:
    port = get_free_port()
    slow_client_id = ClientID(model_name="slow_model", simulator_name="slow_simulator")
    server_run = SimpleTestServer.for_client_ids(
        communication_protocol=communication_protocol,
        host=HOST,
        port=port,
        client_ids=(HEALTHY, slow_client_id),
        steps=STEPS,
        response_timeouts=SHORT_RESPONSE_TIMEOUTS,
    ).start_with_error_recording()
    SimpleTestClient.of_client_id(communication_protocol=communication_protocol, server_host=HOST, server_port=port, client_id=HEALTHY).start()
    SimpleTestClient.of_client_id(
        communication_protocol=communication_protocol,
        server_host=HOST,
        server_port=port,
        client_id=slow_client_id,
        on_simulation_step_return=answer_slowly,
    ).start()

    server_run.assert_ends_within(limit_in_seconds=RUN_LIMIT_IN_SECONDS)
    assert server_run.error is None
