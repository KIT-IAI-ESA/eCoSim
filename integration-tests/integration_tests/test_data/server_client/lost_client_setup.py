import os
import signal
import time
from typing import NoReturn

from ecosim_common.client.client import Client
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_server.simulation.response_timeouts import ResponseTimeouts
from ecosim_test_common.test_data.error_recording_thread import ErrorRecordingThread
from ecosim_test_common.timeouts import SHORT_TIMEOUT_IN_SECONDS
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient

HEALTHY = ClientID(model_name="healthy_model", simulator_name="healthy_simulator")
LOST = ClientID(model_name="lost_model", simulator_name="lost_simulator")
HOST = "localhost"
STEPS = 3
RUN_LIMIT_IN_SECONDS = 30
SHORT_RESPONSE_TIMEOUTS = ResponseTimeouts(
    step_response_timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
    start_response_timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
    restore_connection_check_interval_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
)

Inputs = dict[InterfaceId, InterfaceValue]


def assert_naming_the_lost_client(server_run: ErrorRecordingThread, limit_in_seconds: float, waiting_for: str) -> None:
    server_run.assert_ends_within(limit_in_seconds=limit_in_seconds)
    assert isinstance(server_run.error, RuntimeError), server_run.error
    assert str(LOST) in str(server_run.error)
    assert str(HEALTHY) not in str(server_run.error)
    assert waiting_for in str(server_run.error)


def answer_slowly(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    time.sleep(SHORT_TIMEOUT_IN_SECONDS * 1.5)
    return ClientSimStepData(interface_values=[])


def crash(client: Client) -> NoReturn:
    # closing the channel tells the server this client hung up, and SystemExit ends the listening thread silently
    client.on_app_shutdown()
    raise SystemExit


def crash_in_step(client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    crash(client)


def raise_in_step(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    raise RuntimeError("the model failed")


def kill_own_process(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    os.kill(os.getpid(), signal.SIGKILL)
    raise AssertionError("SIGKILL did not end the process")


def run_client_killing_its_process(port: int) -> None:
    client = SimpleTestClient.of_client_id(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        server_host=HOST,
        server_port=port,
        client_id=LOST,
        on_simulation_step_return=kill_own_process,
    )
    client.start()
    client.wait_until_finished()
