import os
import signal
import time
from typing import Callable, NoReturn

from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from ecosim_test_common.test_data.error_recording_thread import ErrorRecordingThread
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient, TestClientConfig, answer_start
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer, SimpleTestServerParameters, generate_simple_test_server

HEALTHY = ClientID(model_name="healthy_model", simulator_name="healthy_simulator")
LOST = ClientID(model_name="lost_model", simulator_name="lost_simulator")
SLOW = ClientID(model_name="slow_model", simulator_name="slow_simulator")
RUN_LIMIT_IN_SECONDS = 30
SHORT_TIMEOUT_IN_SECONDS = 1
_SLOW_ANSWER_IN_SECONDS = SHORT_TIMEOUT_IN_SECONDS * 1.5
_HOST = "localhost"

Inputs = dict[InterfaceId, InterfaceValue]
StepHandler = Callable[[SimpleTestClient, Inputs, float], ClientSimStepData]
StartHandler = Callable[[SimpleTestClient], ClientSimStepData]


def two_client_server(protocol: CommunicationProtocol, port: int, second_client_id: ClientID, restore: bool = False) -> SimpleTestServer:
    clients = [
        ClientSimulatorConfig(simulator_name=client_id.simulator_name, model_name=client_id.model_name, interfaces=[], client_id=client_id)
        for client_id in (HEALTHY, second_client_id)
    ]
    return generate_simple_test_server(
        SimpleTestServerParameters(communication_protocol=protocol, host=_HOST, port=port, steps=3, restore_simulation_run=restore, clients=clients),
    )


def start_server(server: SimpleTestServer) -> ErrorRecordingThread:
    server_run = ErrorRecordingThread(target=server.start)
    server_run.start()
    return server_run


def assert_failed_naming_the_lost_client(server_run: ErrorRecordingThread, waiting_for: str) -> None:
    server_run.assert_ends_within(limit_in_seconds=RUN_LIMIT_IN_SECONDS)
    assert isinstance(server_run.error, RuntimeError), server_run.error
    assert str(LOST) in str(server_run.error)
    assert str(HEALTHY) not in str(server_run.error)
    assert waiting_for in str(server_run.error)


def answer(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    return ClientSimStepData(interface_values=[])


def answer_slowly(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    time.sleep(_SLOW_ANSWER_IN_SECONDS)
    return ClientSimStepData(interface_values=[])


def crash(client: Client) -> NoReturn:
    # closing the channel tells the server this client hung up, and SystemExit ends the listening thread silently
    client.on_app_shutdown()
    raise SystemExit


def crash_in_step(client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    crash(client)


def kill_own_process(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    os.kill(os.getpid(), signal.SIGKILL)
    raise AssertionError("SIGKILL did not end the process")


def run_client_killing_its_process(port: int) -> None:
    client = new_client(protocol=CommunicationProtocol.TCP_SOCKET, port=port, client_id=LOST, on_step=kill_own_process)
    client.start()
    client.wait_until_finished()


def new_client(
    protocol: CommunicationProtocol,
    port: int,
    client_id: ClientID,
    on_step: StepHandler = answer,
    on_start: StartHandler = answer_start,
) -> SimpleTestClient:
    config = TestClientConfig(
        server_host=_HOST,
        server_port=port,
        simulator_name=client_id.simulator_name,
        model_name=client_id.model_name,
        interface_config=ClientInterfaceConfig(interfaces=[]),
        communication_protocol=protocol,
    )
    return SimpleTestClient(client_config=config, on_simulation_step_return=on_step, on_simulation_start_return=on_start)
