from typing import List

from ecosim_common.client.config.client_type import ClientType


def test_each_matches_serialized() -> None:
    client_types: List[ClientType] = list(ClientType)
    for client_type in client_types:
        assert client_type.matches_string(client_type.serialized)


def test_match_fmu_without_version() -> None:
    client_type = ClientType.of_string("fmu")
    assert client_type == ClientType.FMU_2


def test_match_pyro_without_version() -> None:
    client_type = ClientType.of_string("pyro")
    assert client_type == ClientType.Pyro5
