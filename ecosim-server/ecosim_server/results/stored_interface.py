from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.communication.data.protocol_interface_value import InterfaceValue, ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from ecosim_server.measurement.measurement_repository_db import MeasurementRepositoryDB
from ecosim_server.results.result_column import ResultColumn
from sqlalchemy import RowMapping, Table


@dataclass(frozen=True)
class StoredInterface:
    column: ResultColumn
    number_column: str
    json_column: str

    @staticmethod
    def of_client(client: ClientSimulatorConfig) -> list[StoredInterface]:
        return [
            StoredInterface(
                column=ResultColumn.of_interface(interface),
                number_column=MeasurementRepositoryDB.column_name_of_server_interface(interface),
                json_column=MeasurementRepositoryDB.json_column_name_of_server_interface(interface),
            )
            for interface in client.interfaces
        ]

    @staticmethod
    def of_table(simulator_name: str, table: Table) -> list[StoredInterface]:
        """Reads the interfaces from the column names, i_ or o_ before the lower case name."""
        names = [column.name for column in table.columns]
        return [
            StoredInterface(
                column=ResultColumn(
                    simulator_name=simulator_name,
                    interface_name=name[2:],
                    interface_type=InterfaceType.INPUT if name.startswith("i_") else InterfaceType.OUTPUT,
                ),
                number_column=name,
                json_column=f"{name}_json",
            )
            for name in names
            if f"{name}_json" in names
        ]

    def interface_value_of(self, row: RowMapping) -> ProtocolInterfaceValue:
        number: InterfaceValue = row.get(self.number_column)
        return ProtocolInterfaceValue(name=self.column.interface_name, value=number if number is not None else row.get(self.json_column))
