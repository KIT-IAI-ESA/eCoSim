import threading
from time import sleep

import dask.distributed as dd
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.dask import dask_channel
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.port_utils import get_free_port
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServerParameters, generate_simple_test_server

_RECEIVE_TIMEOUT_NAME = "_DEFAULT_RECEIVE_TIMEOUT_IN_SECONDS"
_SHORT_RECEIVE_TIMEOUT_IN_SECONDS = 1
_STEP_IN_SECONDS = 3
_STEPS = 2
_RUN_BOUND_IN_SECONDS = 60


def _shorten_receive_timeout() -> None:
    setattr(dask_channel, _RECEIVE_TIMEOUT_NAME, _SHORT_RECEIVE_TIMEOUT_IN_SECONDS)


def _slow_step(_client: SimpleTestClient, _received_inputs: dict[InterfaceId, InterfaceValue], _step_size: float) -> ClientSimStepData:
    sleep(_STEP_IN_SECONDS)
    return ClientSimStepData(interface_values=[])


def test_a_step_longer_than_the_receive_timeout_does_not_end_the_run(dask_client: dd.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    # the server reads its connections on the workers and the client reads here
    dask_client.run(_shorten_receive_timeout)
    monkeypatch.setattr(dask_channel, _RECEIVE_TIMEOUT_NAME, _SHORT_RECEIVE_TIMEOUT_IN_SECONDS)
    server_host = "localhost"
    server_port = get_free_port()
    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=CommunicationProtocol.DASK,
            host=server_host,
            port=server_port,
            steps=_STEPS,
        ),
    )
    client = SimpleTestClient.generate(
        communication_protocol=CommunicationProtocol.DASK,
        server_host=server_host,
        server_port=server_port,
        on_simulation_step_return=_slow_step,
    )

    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    client.start()
    server_thread.join(timeout=_RUN_BOUND_IN_SECONDS)

    assert not server_thread.is_alive(), "the run did not finish"
    measurement_repository = server.measurement_repository(client_id=client.client_id)
    assert isinstance(measurement_repository, MeasurementRepositoryInMemory)
    measurement_repository.assert_entry_count(_STEPS)
