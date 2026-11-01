import threading
from typing import Callable, List, NoReturn

from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient, TestClientConfig
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer, SimpleTestServerParameters, generate_simple_test_server

HEALTHY = ClientID(model_name="healthy_model", simulator_name="healthy_simulator")
LOST = ClientID(model_name="lost_model", simulator_name="lost_simulator")
RUN_LIMIT_IN_SECONDS = 30
_HOST = "localhost"

Inputs = dict[InterfaceId, InterfaceValue]
StepHandler = Callable[[SimpleTestClient, Inputs, float], ClientSimStepData]


def lost_client_server(protocol: CommunicationProtocol, port: int, restore: bool = False) -> SimpleTestServer:
    clients = [
        ClientSimulatorConfig(simulator_name=client_id.simulator_name, model_name=client_id.model_name, interfaces=[], client_id=client_id)
        for client_id in (HEALTHY, LOST)
    ]
    return generate_simple_test_server(
        SimpleTestServerParameters(communication_protocol=protocol, host=_HOST, port=port, steps=3, restore_simulation_run=restore, clients=clients),
    )


def start_server(server: SimpleTestServer) -> tuple[threading.Thread, List[Exception]]:
    errors: List[Exception] = []

    def run() -> None:
        try:
            server.start()
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, errors


def assert_run_ended(thread: threading.Thread) -> None:
    thread.join(RUN_LIMIT_IN_SECONDS)
    assert not thread.is_alive(), f"the server still hangs after {RUN_LIMIT_IN_SECONDS}s"


def assert_failed_naming_the_lost_client(thread: threading.Thread, errors: List[Exception]) -> None:
    assert_run_ended(thread)
    assert len(errors) == 1
    assert str(LOST) in str(errors[0])
    assert str(HEALTHY) not in str(errors[0])


def answer(_client: SimpleTestClient, _inputs: Inputs, _step_size: float) -> ClientSimStepData:
    return ClientSimStepData(interface_values=[])


def crash(client: Client) -> NoReturn:
    # the channel hangs up like the one of a dead process, and SystemExit ends the listening thread silently
    client.on_app_shutdown()
    raise SystemExit


def new_client(
    protocol: CommunicationProtocol,
    port: int,
    client_id: ClientID,
    on_step: StepHandler = answer,
    client_type: type[SimpleTestClient] = SimpleTestClient,
) -> SimpleTestClient:
    config = TestClientConfig(
        server_host=_HOST,
        server_port=port,
        simulator_name=client_id.simulator_name,
        model_name=client_id.model_name,
        interface_config=ClientInterfaceConfig(interfaces=[]),
        communication_protocol=protocol,
    )
    return client_type(client_config=config, on_simulation_step_return=on_step)
