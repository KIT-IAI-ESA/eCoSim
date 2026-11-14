from unittest.mock import MagicMock

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.client.client_states import ClientStates
from tests.data.generate_postgres_name_config import generate_client_simulator_config, generate_simulation_config
from tests.data.generate_server_config import generate_server_config
from tests.data.generate_simulation_config import HOUSE, WEATHER


def _client_states_of_house_and_weather() -> ClientStates:
    return ClientStates.for_config(
        server_config=generate_server_config(),
        simulation_config=generate_simulation_config(
            clients=[generate_client_simulator_config(simulator_name=client_id.simulator_name) for client_id in (HOUSE, WEATHER)],
        ),
    )


def _connect(client_states: ClientStates, client_id: ClientID) -> bool:
    return client_states.add_if_needed(
        client_config=ClientMetaData(version="2.0", simulator_name=client_id.simulator_name, model_name=client_id.model_name),
        client_connection=ClientConnection(_channel=MagicMock(spec=ESPChannel), address=ConnectionAddress(ip="127.0.0.1", port=1)),
    )


def test_the_server_waits_for_the_clients_that_are_not_connected_and_ready() -> None:
    client_states = _client_states_of_house_and_weather()
    _connect(client_states=client_states, client_id=WEATHER)
    client_states.set_client_ready_for_simulation(client_id=WEATHER)
    _connect(client_states=client_states, client_id=HOUSE)

    assert client_states.waiting_for_client_ids() == (HOUSE,)


def test_a_client_with_a_misspelt_simulator_name_is_turned_away_and_still_waited_for() -> None:
    client_states = _client_states_of_house_and_weather()

    accepted = _connect(client_states=client_states, client_id=ClientID(model_name="house", simulator_name="hous"))

    assert not accepted
    assert client_states.waiting_for_client_ids() == (HOUSE, WEATHER)


def test_the_server_waits_for_the_models_that_have_not_started() -> None:
    client_states = _client_states_of_house_and_weather()

    client_states.simulation_started(client_id=WEATHER)

    assert client_states.not_started_client_ids() == (HOUSE,)
