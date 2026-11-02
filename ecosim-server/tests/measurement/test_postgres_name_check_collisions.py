from __future__ import annotations

import pytest
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.measurement.postgres_name_check import check_names_fit_postgres_storage
from tests.data.generate_postgres_name_config import a_config, a_simulator, error_of

INPUT = InterfaceType.INPUT
OUTPUT = InterfaceType.OUTPUT
BIND_NAME_PAIRS = [("p.T", "p_T"), ("T[1]", "T_1_"), ("a b", "a_b"), ("p.1..T", "p[1].T")]


@pytest.mark.parametrize("interface_type", [INPUT, OUTPUT])
@pytest.mark.parametrize("names", [("T", "t"), ("x", "x_json")])
def test_interfaces_sharing_a_column_are_rejected_once(names: tuple[str, str], interface_type: InterfaceType) -> None:
    message = error_of(a_simulator("house", (names[0], interface_type), (names[1], interface_type)))

    assert message.count(f"simulator 'house': interfaces '{names[0]}', '{names[1]}' would share one column") == 1
    assert "written with one value" not in message


@pytest.mark.parametrize("names", [("T", "t"), ("x", "x_json"), ("p.T", "p_T")])
def test_an_input_and_an_output_keep_their_own_columns(names: tuple[str, str]) -> None:
    check_names_fit_postgres_storage(a_config(a_simulator("house", (names[0], INPUT), (names[1], OUTPUT))))


@pytest.mark.parametrize("types", [(INPUT, OUTPUT), (OUTPUT, OUTPUT), (INPUT, INPUT)])
def test_the_same_interface_name_twice_is_rejected(types: tuple[InterfaceType, InterfaceType]) -> None:
    message = error_of(a_simulator("house", ("T", types[0]), ("T", types[1])))

    assert "simulator 'house', interface 'T': the name is used by 2 interfaces" in message


def test_the_same_interface_name_in_two_simulators_is_fine() -> None:
    check_names_fit_postgres_storage(a_config(a_simulator("house", ("T", OUTPUT)), a_simulator("heating", ("T", OUTPUT))))


@pytest.mark.parametrize("interface_type", [INPUT, OUTPUT])
@pytest.mark.parametrize("names", BIND_NAME_PAIRS)
def test_interfaces_sharing_a_bind_name_are_rejected_once(names: tuple[str, str], interface_type: InterfaceType) -> None:
    message = error_of(a_simulator("house", (names[0], interface_type), (names[1], interface_type)))

    assert message.count(f"simulator 'house': interfaces '{names[0]}', '{names[1]}' would be written with one value") == 1


def test_simulators_differing_only_in_case_are_rejected() -> None:
    assert "simulators 'T', 't' differ only in case" in error_of(a_simulator("T", ("a", OUTPUT)), a_simulator("t", ("a", OUTPUT)))


def test_interfaces_of_different_simulators_differing_only_in_case_have_their_own_tables() -> None:
    check_names_fit_postgres_storage(a_config(a_simulator("house", ("T", OUTPUT)), a_simulator("heating", ("t", OUTPUT))))


def test_two_simulators_with_the_same_name_and_different_models_are_rejected() -> None:
    message = error_of(a_simulator("house", ("a", OUTPUT), model="first"), a_simulator("house", ("b", OUTPUT), model="second"))

    assert "simulator 'house': the name is used by 2 simulators, which would share one table" in message
