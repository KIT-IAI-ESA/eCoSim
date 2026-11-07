from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, List, Tuple, override

from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.tech.logger.logger import ESPLogger
from sqlalchemy import FLOAT, JSON, Column, DateTime

from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base


@dataclass(frozen=True)
class MeasurementRepositoryDB(MeasurementRepository):
    _logger: ClassVar[ESPLogger] = ESPLogger("MeasurementRepositoryDB")

    _db_connection: DBConnection = field()
    _dynamic_table: type = field()
    _interface_name_to_column_name: dict[str, str] = field()
    _interface_name_to_json_column_name: dict[str, str] = field()

    @staticmethod
    def create(
        simulation_config: SimulationConfig,
        client_id: ClientID,
        db_connection: DBConnection,
    ) -> MeasurementRepositoryDB:
        client_config = simulation_config.client_simulator_config_for(client_id)
        if client_config is None:
            raise RuntimeError(f"No config for clientID {client_id} found.")
        interface_name_to_column_name = MeasurementRepositoryDB._create_interface_name_to_column_name(client_config)
        interface_name_to_json_column_name = MeasurementRepositoryDB._create_interface_name_to_json_column_name(client_config)
        dynamic_table = MeasurementRepositoryDB._create_dynamic_class(
            client_config=client_config,
            interface_name_to_column_name=interface_name_to_column_name,
            interface_name_to_json_column_name=interface_name_to_json_column_name,
        )
        db_connection.create_measurement_table(dynamic_table)
        return MeasurementRepositoryDB(
            _db_connection=db_connection,
            _dynamic_table=dynamic_table,
            _interface_name_to_column_name=interface_name_to_column_name,
            _interface_name_to_json_column_name=interface_name_to_json_column_name,
        )

    @staticmethod
    def _create_dynamic_class(
        client_config: ClientSimulatorConfig,
        interface_name_to_column_name: dict[str, str],
        interface_name_to_json_column_name: dict[str, str],
    ) -> type:
        table_name = f"module_{client_config.simulator_name.lower()}"

        attributes = {
            "__tablename__": table_name,
            "timestamp": Column(DateTime(timezone=True), primary_key=True),
        }
        for column_name in interface_name_to_column_name.values():
            attributes[column_name] = Column(FLOAT)
        for column_name in interface_name_to_json_column_name.values():
            attributes[column_name] = Column(JSON)

        dynamic_class = type(table_name, (SimControlDB_Base,), attributes)
        return dynamic_class

    @staticmethod
    def _create_interface_name_to_column_name(
        client_config: ClientSimulatorConfig,
    ) -> dict[str, str]:
        interface_name_to_column_name: dict[str, str] = {}
        for interface in client_config.interfaces:
            column_name = MeasurementRepositoryDB.column_name_of_server_interface(interface)
            interface_name_to_column_name[interface.name] = column_name
        return interface_name_to_column_name

    @staticmethod
    def _create_interface_name_to_json_column_name(
        client_config: ClientSimulatorConfig,
    ) -> dict[str, str]:
        interface_name_to_json_column_name: dict[str, str] = {}
        for interface in client_config.interfaces:
            column_name = MeasurementRepositoryDB.json_column_name_of_server_interface(interface)
            interface_name_to_json_column_name[interface.name] = column_name
        return interface_name_to_json_column_name

    @staticmethod
    def column_name_of_server_interface(interface: ModelInterfaceServer) -> str:
        return f"{'i' if interface.type == InterfaceType.INPUT else 'o'}_{interface.name.lower()}"

    @staticmethod
    def json_column_name_of_server_interface(interface: ModelInterfaceServer) -> str:
        return f"{'i' if interface.type == InterfaceType.INPUT else 'o'}_{interface.name.lower()}_json"

    def _select_column(
        self,
        value: ProtocolInterfaceValue,
    ) -> str:
        if isinstance(value.value, float):
            return self._interface_name_to_column_name[value.name]
        elif isinstance(value.value, Sequence) and not isinstance(value.value, (str, bytes)):  # type: ignore
            # ignore match on str or bytes -> the exclusion is implemented as a failsafe if at any time str or bytes is a valid value type
            return self._interface_name_to_json_column_name[value.name]
        self._logger.error("Unknown value type: %s -> handling it as json, but you need to fix this.", type(value.value))
        return self._interface_name_to_json_column_name[value.name]

    @override
    def add(
        self,
        values: Tuple[ProtocolInterfaceValue, ...],
        timestamp: datetime.datetime,
    ) -> None:
        with self._db_connection.session() as session:
            new_record = self._dynamic_table(
                timestamp=timestamp,
                **{f"{self._select_column(v)}": v.value for v in values},
            )
            session.add(new_record)
            session.commit()

    @override
    def all(self) -> List[MeasurementEntry]:
        result: List[MeasurementEntry] = []
        with self._db_connection.session() as session:
            ts_col = getattr(self._dynamic_table, "timestamp")
            rows: List[Any] = session.query(self._dynamic_table).order_by(ts_col.asc()).all()
            for row in rows:
                values_list: List[ProtocolInterfaceValue] = []
                # First, collect scalar (float) values
                for interface_name, column_name in self._interface_name_to_column_name.items():
                    val = getattr(row, column_name)
                    if val is not None:
                        values_list.append(ProtocolInterfaceValue(name=interface_name, value=val))
                # Then, collect JSON (sequence) values
                for interface_name, json_column_name in self._interface_name_to_json_column_name.items():
                    val = getattr(row, json_column_name)
                    if val is not None:
                        values_list.append(ProtocolInterfaceValue(name=interface_name, value=val))
                # Deterministic order by interface name
                values_list.sort(key=lambda v: str(v.name))
                result.append(MeasurementEntry(values=tuple(values_list), timestamp=row.timestamp))
        return result

    @override
    def remove_starting_at(self, timestamp: datetime.datetime) -> None:
        with self._db_connection.session() as session:
            timestamp_column = getattr(self._dynamic_table, "timestamp")
            session.query(self._dynamic_table).filter(timestamp_column >= timestamp).delete()
            session.commit()
