from unittest.mock import MagicMock

from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_states import ClientStates
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from tests.data.generate_server_config import generate_server_config

_READY_CLIENT_ID = ClientID(model_name="ready_model", simulator_name="simulator")
_NOT_READY_CLIENT_ID = ClientID(model_name="not_ready_model", simulator_name="simulator")


def _client_config(client_id: ClientID) -> ClientSimulatorConfig:
    return ClientSimulatorConfig(simulator_name=client_id.simulator_name, model_name=client_id.model_name, interfaces=[], client_id=client_id)


def test_connected_client_that_is_not_ready_counts_as_lost() -> None:
    client_states = ClientStates.for_config(
        server_config=generate_server_config(),
        simulation_config=MagicMock(spec=SimulationConfig, clients=[_client_config(_READY_CLIENT_ID), _client_config(_NOT_READY_CLIENT_ID)]),
    )
    client_states.set_client_connected_state(client_id=_READY_CLIENT_ID, connected=True)
    client_states.set_client_connected_state(client_id=_NOT_READY_CLIENT_ID, connected=True)
    client_states.set_client_ready_for_simulation(_READY_CLIENT_ID)

    assert client_states.lost_client_ids(client_ids=(_READY_CLIENT_ID, _NOT_READY_CLIENT_ID)) == (_NOT_READY_CLIENT_ID,)
