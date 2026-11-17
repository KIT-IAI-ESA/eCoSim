from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.results.result_column import ColumnValue, ResultColumn, numbers_by_index
from ecosim_server.results.result_table import ResultTable
from ecosim_server.simulation.state.simulation_state import SimulationState

# interface name and position in an array
type CellKey = tuple[str, tuple[int, ...]]


@dataclass
class ResultTableBuilder:
    _cells: dict[datetime, dict[int, ColumnValue]] = field(default_factory=lambda: defaultdict(dict))
    _columns: list[ResultColumn] = field(default_factory=list)

    def add_simulator(self, simulator_name: str, entries: Sequence[MeasurementEntry], described_columns: Sequence[ResultColumn]) -> None:
        cells_by_time = self._cells_of(entries=entries)
        keys = list(dict.fromkeys(key for cells in cells_by_time.values() for key in cells))
        columns = _columns_in_order(simulator_name=simulator_name, keys=keys, described_columns=described_columns)
        position_by_key = {(column.interface_name, column.index): len(self._columns) + offset for offset, column in enumerate(columns)}
        for time, cells in cells_by_time.items():
            self._cells[time].update({position_by_key[key]: value for key, value in cells.items()})
        self._columns += columns

    def build(self, state: SimulationState | None, warnings: Sequence[str]) -> ResultTable:
        times = sorted(self._cells)
        positions = range(len(self._columns))
        return ResultTable(
            columns=tuple(self._columns),
            times=tuple(times),
            rows=tuple(tuple(self._cells[time].get(position) for position in positions) for time in times),
            state=state,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _cells_of(entries: Sequence[MeasurementEntry]) -> dict[datetime, dict[CellKey, ColumnValue]]:
        cells_by_time: dict[datetime, dict[CellKey, ColumnValue]] = defaultdict(dict)
        for entry in entries:
            cells = cells_by_time[entry.timestamp]
            for value in entry.values:
                if value.value is None:
                    continue
                for index, number in numbers_by_index(value=value.value):
                    cells[(value.name, index)] = number
        return cells_by_time


def _columns_in_order(simulator_name: str, keys: Sequence[CellKey], described_columns: Sequence[ResultColumn]) -> list[ResultColumn]:
    column_by_name = {column.interface_name: column for column in described_columns}
    for interface_name, _ in keys:
        column_by_name.setdefault(interface_name, ResultColumn(simulator_name=simulator_name, interface_name=interface_name, interface_type=None))
    order = {interface_name: position for position, interface_name in enumerate(column_by_name)}
    columns = [column_by_name[interface_name].for_index(index) for interface_name, index in keys]
    return sorted(columns, key=lambda column: (column.is_input, order[column.interface_name], column.index))
