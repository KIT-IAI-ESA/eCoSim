from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository_db import MeasurementRepositoryDB
from ecosim_server.results.result_table import ResultTable
from ecosim_server.results.result_table_builder import ResultTableBuilder
from ecosim_server.results.stored_interface import StoredInterface
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository_db import SimulationStateDTO
from ecosim_server.tech.db.db_connection import DBConnection
from sqlalchemy import Connection, MetaData, Table, inspect, select, true
from sqlalchemy.exc import OperationalError

_logger = ESPLogger("DatabaseResults")


def read_database_results(database: DatabaseConfig, simulation_config: str | Path | None = None, include_inputs: bool = False) -> ResultTable:
    """The results a run wrote to PostgreSQL as one table, by default without the inputs, with the times in UTC."""
    config_file = None if simulation_config is None else Path(simulation_config)
    clients = None if config_file is None else SimulationConfig.clients_of_file(config_file)
    table = DatabaseResults.read(database=database, simulation_config_file=config_file, clients=clients)
    return table if include_inputs else table.without_inputs()


@dataclass(frozen=True)
class DatabaseResults:
    """The schema a run wrote to and the simulators of the run's simulation.json, None without one. It only reads."""

    connection: Connection
    database: DatabaseConfig
    simulation_config_file: Path | None
    clients: list[ClientSimulatorConfig] | None

    @staticmethod
    def read(database: DatabaseConfig, simulation_config_file: Path | None, clients: list[ClientSimulatorConfig] | None) -> ResultTable:
        engine = DBConnection.engine_of(database)
        try:
            with engine.connect() as connection:
                results = DatabaseResults(connection=connection, database=database, simulation_config_file=simulation_config_file, clients=clients)
                return results.table()
        except OperationalError as error:
            # the text of SQLAlchemy adds a link to its docs, the first line of psycopg's text says what went wrong
            reason = str(error.orig).splitlines()[0]
            raise ConnectionError(f"Cannot read the results from PostgreSQL at {database.server_location()}: {reason}.") from error
        finally:
            engine.dispose()

    def table(self) -> ResultTable:
        table_names = self._table_names()
        module_tables = [name for name in table_names if name.startswith("module_")]
        builder = ResultTableBuilder()
        for simulator_name, client in self._simulators_to_read(module_tables=module_tables):
            self._add_simulator(builder=builder, simulator_name=simulator_name, client=client)
        warnings = self._config_warnings(module_tables=module_tables)
        for warning in warnings:
            _logger.warning("%s", warning)
        state = self._state() if SimulationStateDTO.__tablename__ in table_names else None
        return builder.build(state=state, warnings=warnings)

    def _table_names(self) -> list[str]:
        inspector = inspect(self.connection)
        schema = self.database.schema
        if schema not in inspector.get_schema_names():
            raise RuntimeError(
                f"The database {self.database.name} has no schema {schema}. Give the schema the server wrote to, its --database-schema.",
            )
        return list(inspector.get_table_names(schema=schema))

    def _simulators_to_read(self, module_tables: list[str]) -> list[tuple[str, ClientSimulatorConfig | None]]:
        if not module_tables:
            raise RuntimeError(f"The schema {self.database.schema} holds no results: it has no module_<simulator> table.")
        if self.clients is None:
            return [(name.removeprefix("module_"), None) for name in sorted(module_tables)]
        stored = [client for client in self.clients if MeasurementRepositoryDB.table_name_of(simulator_name=client.simulator_name) in module_tables]
        if not stored:
            listed, config_file = ", ".join(client.simulator_name for client in self.clients), self.simulation_config_file
            raise ValueError(f"The schema {self.database.schema} holds no results of the simulators that {config_file} lists: {listed}.")
        return [(client.simulator_name, client) for client in stored]

    def _add_simulator(self, builder: ResultTableBuilder, simulator_name: str, client: ClientSimulatorConfig | None) -> None:
        table_name = MeasurementRepositoryDB.table_name_of(simulator_name=simulator_name)
        # a MetaData of its own, since the server's one defines each table once per process
        table = Table(table_name, MetaData(), schema=self.database.schema, autoload_with=self.connection)
        if client is None:
            interfaces = StoredInterface.of_table(simulator_name=simulator_name, table=table)
        else:
            interfaces = StoredInterface.of_client(client=client)
        entries = self._entries_of(table=table, interfaces=interfaces)
        builder.add_simulator(simulator_name=simulator_name, entries=entries, described_columns=[interface.column for interface in interfaces])

    def _entries_of(self, table: Table, interfaces: list[StoredInterface]) -> list[MeasurementEntry]:
        rows = self.connection.execute(select(table).order_by(table.c.timestamp)).mappings()
        return [
            MeasurementEntry(
                values=tuple(interface.interface_value_of(row=row) for interface in interfaces),
                # psycopg gives the times in the time zone of the database session
                timestamp=row["timestamp"].astimezone(timezone.utc),
            )
            for row in rows
        ]

    def _config_warnings(self, module_tables: list[str]) -> list[str]:
        if self.clients is None:
            return ["PostgreSQL stores the names in lower case. Give the run's simulation.json to get them as written there."]
        listed = {MeasurementRepositoryDB.table_name_of(simulator_name=client.simulator_name): client.simulator_name for client in self.clients}
        schema, config_file = self.database.schema, self.simulation_config_file
        missing = [name for table, name in listed.items() if table not in module_tables]
        unlisted = [table for table in module_tables if table not in listed and self._holds_rows(table_name=table)]
        return [
            *(f"The schema {schema} has no results of {name}, which {config_file} lists." for name in missing),
            *(f"{config_file} does not list {table.removeprefix('module_')}, so the table leaves out {schema}.{table}." for table in unlisted),
        ]

    def _holds_rows(self, table_name: str) -> bool:
        # an empty table holds no results to leave out, and a server process also creates empty ones
        first_row = select(true()).select_from(Table(table_name, MetaData(), schema=self.database.schema)).limit(1)
        return self.connection.execute(first_row).first() is not None

    def _state(self) -> SimulationState | None:
        newest_state = select(SimulationStateDTO.state).order_by(SimulationStateDTO.state_id.desc()).limit(1)
        state = self.connection.execute(newest_state).scalar()
        return SimulationState.of_db_entry(state) if state else None
