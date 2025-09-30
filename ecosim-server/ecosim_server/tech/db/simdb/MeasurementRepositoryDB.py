import datetime
from collections.abc import Sequence
from typing import Tuple, override, List, Any

from sqlalchemy import Column, DateTime, Float, JSON

from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.tech.db.db_connections import DBConnections
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.measurement_repository import MeasurementRepository


class MeasurementRepositoryDB(MeasurementRepository):
    _logger = ESPLogger("MeasurementRepositoryDB")

    def __init__(self,
                 simulation_config: SimulationConfig,
                 client_id: ClientID,
                 ):
        self._db_connection = DBConnections.instance().main
        self._interface_name_to_column_name: dict[str, str] = {}
        self._interface_name_to_json_column_name: dict[str, str] = {}
        self._DynamicTable = self._create_dynamic_class(simulation_config, client_id)
        self._db_connection.create_measurement_table(self._DynamicTable)

    def _create_dynamic_class(self,
                              simulation_config: SimulationConfig,
                              client_id: ClientID
                              ) -> type:
        client_config = simulation_config.client_simulator_config_for(client_id)
        if client_config is None:
            raise RuntimeError(f"No config for clientID {client_id} found.")
        table_name = f"module_{client_config.simulator_name.lower()}"

        attributes = {
            '__tablename__': table_name,
            '__table_args__': {'schema': self._db_connection.default_schema},
            'timestamp': Column(DateTime(timezone=True), primary_key=True)
        }
        for interface in client_config.interfaces:
            column_name = MeasurementRepositoryDB._column_name_of_server_interface(interface)
            self._interface_name_to_column_name[interface.name] = column_name
            attributes[column_name] = Column(Float)
            json_column_name = MeasurementRepositoryDB._json_column_name_of_server_interface(interface)
            self._interface_name_to_json_column_name[interface.name] = json_column_name
            attributes[json_column_name] = Column(JSON)

        dynamic_class = type(table_name, (SimControlDB_Base,), attributes)
        return dynamic_class

    @staticmethod
    def _column_name_of_server_interface(interface: ModelInterfaceServer) -> str:
        return f"{'i' if interface.type == InterfaceType.INPUT else 'o'}_{interface.name.lower()}"

    @staticmethod
    def _json_column_name_of_server_interface(interface: ModelInterfaceServer) -> str:
        return f"{'i' if interface.type == InterfaceType.INPUT else 'o'}_{interface.name.lower()}_json"

    def _select_column(self,
                       value: ProtocolInterfaceValue,
                       ) -> str:
        if isinstance(value.value, float):
            return self._interface_name_to_column_name[value.name]
        elif isinstance(value.value, Sequence) and not isinstance(value.value, (str, bytes)):  # type: ignore
            # ignore match on str or bytes -> the exclusion is implemented as a failsafe if at any time str or bytes is a valid value type
            return self._interface_name_to_json_column_name[value.name]
        self._logger.error(f"Unknown value type: {type(value.value)} -> handling it as json, but you need to fix this.")
        return self._interface_name_to_json_column_name[value.name]

    @override
    def add(self,
            values: Tuple[ProtocolInterfaceValue, ...],
            timestamp: datetime.datetime,
            ) -> None:
        with self._db_connection.session() as session:
            new_record = self._DynamicTable(
                timestamp=timestamp,
                **{f"{self._select_column(v)}": v.value for v in values},
            )
            session.add(new_record)
            session.commit()

    @override
    def all(self) -> List[MeasurementEntry]:
        result: List[MeasurementEntry] = []
        with self._db_connection.session() as session:
            ts_col = getattr(self._DynamicTable, 'timestamp')
            rows: List[Any] = session.query(self._DynamicTable).order_by(ts_col.asc()).all()
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
