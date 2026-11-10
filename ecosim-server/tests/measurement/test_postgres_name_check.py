from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import create_repositories
from ecosim_server.measurement.postgres_name_check import check_names_fit_postgres_storage
from ecosim_server.tech.db.postgres_tech import PostgresTech
from ecosim_test_common.resources.config_files import config_file_path
from tests.data.generate_postgres_name_config import START_DATE, error_of, generate_client_simulator_config, generate_simulation_config
from tests.data.generate_server_config import generate_server_config

INPUT = InterfaceType.INPUT
OUTPUT = InterfaceType.OUTPUT
LONG_NAME = "a" * 70
KELVIN_SIGN = "K"
DOTTED_CAPITAL_I = "İ"


@pytest.mark.parametrize(("name", "size"), [(LONG_NAME, 70), ("a" * 61, 61), ("ä" * 31, 62)])
def test_a_long_interface_name_is_rejected_with_its_simulator_and_size(name: str, size: int) -> None:
    message = error_of(generate_client_simulator_config(simulator_name="house", interfaces=[(name, OUTPUT)]))

    assert f"simulator 'house', interface '{name}': the name takes {size} bytes" in message


@pytest.mark.parametrize(("name", "size"), [("s" * 57, 57), ("ä" * 29, 58), (DOTTED_CAPITAL_I * 19, 57)])
def test_a_long_simulator_name_is_rejected_with_the_limit(name: str, size: int) -> None:
    message = error_of(generate_client_simulator_config(simulator_name=name, interfaces=[("a", OUTPUT)]))

    assert f"simulator '{name}': the name takes {size} bytes, at most 56 fit" in message


@pytest.mark.parametrize(
    ("simulator", "interface"),
    [("s" * 56, "a" * 60), ("ä" * 28, "ä" * 30), (KELVIN_SIGN * 56, "a"), (DOTTED_CAPITAL_I * 18 + "ab", "a")],
)
def test_names_at_the_limits_fit(simulator: str, interface: str) -> None:
    check_names_fit_postgres_storage(
        generate_simulation_config(clients=[generate_client_simulator_config(simulator_name=simulator, interfaces=[(interface, OUTPUT)])]),
    )


def test_all_problems_are_reported_together() -> None:
    message = error_of(
        generate_client_simulator_config(simulator_name="T", interfaces=[(LONG_NAME, OUTPUT)]),
        generate_client_simulator_config(simulator_name="t", interfaces=[("A", INPUT), ("a", INPUT)]),
    )

    assert LONG_NAME in message
    assert "simulators 'T', 't'" in message
    assert "interfaces 'A', 'a'" in message


@pytest.mark.parametrize("file_name", ["simulation.json", "simulation_bergwald.json", "simulation_without_start_date.json"])
def test_the_test_configs_fit(file_name: str) -> None:
    check_names_fit_postgres_storage(SimulationConfig.of_config_file_and_params(simulation_config_file=config_file_path(file_name), steps=1))


def test_the_postgres_repositories_reject_such_names_before_touching_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db = MagicMock()
    monkeypatch.setattr(PostgresTech, "init_db", init_db)

    with pytest.raises(RuntimeError, match=LONG_NAME):
        create_repositories(
            server_config=generate_server_config(database_type=DatabaseType.POSTGRES),
            simulation_config=generate_simulation_config(
                clients=[generate_client_simulator_config(simulator_name="house", interfaces=[(LONG_NAME, OUTPUT)])],
            ),
        )

    init_db.assert_not_called()


def test_the_file_repositories_keep_such_names(tmp_path: Path) -> None:
    names = (LONG_NAME, "T", "t", "x", "x_json", "p.T", "p_T")
    client = generate_client_simulator_config(simulator_name="s" * 57, interfaces=[("T", INPUT), *[(name, OUTPUT) for name in names]])
    repositories = create_repositories(
        server_config=generate_server_config(database_type=DatabaseType.FILE, database_directory=tmp_path),
        simulation_config=generate_simulation_config(clients=[client]),
    )
    repository = repositories.measurement_repository(client.client_id)
    values = tuple(ProtocolInterfaceValue(name=name, value=float(index)) for index, name in enumerate(names))

    repository.add(values=values, timestamp=START_DATE)

    assert repository.all()[0].values == values
