from collections import Counter, defaultdict
from typing import Iterable

from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.measurement_repository_db import MeasurementRepositoryDB
from sqlalchemy.dialects.postgresql.psycopg import dialect

IDENTIFIER_LIMIT_IN_BYTES = 63
MAXIMUM_SIMULATOR_NAME_IN_BYTES = IDENTIFIER_LIMIT_IN_BYTES - len("module_")
# one byte less than fits, because at the full size the number column equals the cut JSON column
MAXIMUM_INTERFACE_NAME_IN_BYTES = IDENTIFIER_LIMIT_IN_BYTES - len("i_") - 1
# SQLAlchemy renders 'p.t' and 'p_t' as one bind name, so both columns get the same value
BIND_NAME_TRANSLATION = str.maketrans(dict(dialect.statement_compiler.bindname_escape_characters))


def check_names_fit_postgres_storage(simulation_config: SimulationConfig) -> None:
    clients = simulation_config.clients
    problems = [*_problems_of_simulator_names(clients), *[problem for client in clients for problem in _problems_of_interface_names(client)]]
    if problems:
        lines = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(f"The simulation config has names the PostgreSQL storage cannot hold:\n{lines}")


def _problems_of_simulator_names(clients: list[ClientSimulatorConfig]) -> list[str]:
    names = [client.simulator_name for client in clients]
    too_long = [
        f"simulator '{name}': the name takes {_size(name)} bytes, at most {MAXIMUM_SIMULATOR_NAME_IN_BYTES} fit"
        for name in names
        if _size(name) > MAXIMUM_SIMULATOR_NAME_IN_BYTES
    ]
    repeated = [
        f"simulator '{name}': the name is used by {count} simulators, which would share one table" for name, count in _repeated(names).items()
    ]
    case_only = _names_sharing_a_key((name.lower(), name) for name in names)
    return too_long + repeated + [f"simulators {_quoted(group)} differ only in case, but would share one table" for group in case_only]


def _problems_of_interface_names(client: ClientSimulatorConfig) -> list[str]:
    simulator = f"simulator '{client.simulator_name}'"
    names = [interface.name for interface in client.interfaces]
    too_long = [
        f"{simulator}, interface '{name}': the name takes {_size(name)} bytes, at most {MAXIMUM_INTERFACE_NAME_IN_BYTES} fit"
        for name in names
        if _size(name) > MAXIMUM_INTERFACE_NAME_IN_BYTES
    ]
    repeated = [
        f"{simulator}, interface '{name}': the name is used by {count} interfaces, but the storage keeps one column per name"
        for name, count in _repeated(names).items()
    ]
    return [*too_long, *repeated, *[f"{simulator}: {problem}" for problem in _problems_of_columns(client)]]


def _problems_of_columns(client: ClientSimulatorConfig) -> list[str]:
    columns = [(column, interface.name) for interface in client.interfaces for column in _columns_of(interface)]
    same_column = _names_sharing_a_key(columns)
    same_bind_name = _names_sharing_a_key((column.translate(BIND_NAME_TRANSLATION), name) for column, name in columns)
    return [
        *[f"interfaces {_quoted(group)} would share one column" for group in same_column],
        *[f"interfaces {_quoted(group)} would be written with one value" for group in same_bind_name if group not in same_column],
    ]


def _size(name: str) -> int:
    return len(name.lower().encode())


def _repeated(names: list[str]) -> dict[str, int]:
    return {name: count for name, count in Counter(names).items() if count > 1}


def _columns_of(interface: ModelInterfaceServer) -> tuple[str, str]:
    return (
        MeasurementRepositoryDB.column_name_of_server_interface(interface),
        MeasurementRepositoryDB.json_column_name_of_server_interface(interface),
    )


def _names_sharing_a_key(keys_and_names: Iterable[tuple[str, str]]) -> list[tuple[str, ...]]:
    names_by_key: dict[str, set[str]] = defaultdict(set)
    for key, name in keys_and_names:
        names_by_key[key].add(name)
    # 'T' and 't' share both their columns, which is one problem
    return list(dict.fromkeys(tuple(sorted(names)) for names in names_by_key.values() if len(names) > 1))


def _quoted(names: tuple[str, ...]) -> str:
    return ", ".join(f"'{name}'" for name in names)
