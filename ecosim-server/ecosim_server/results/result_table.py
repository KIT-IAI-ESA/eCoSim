from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from ecosim_common.tech.close_name import did_you_mean
from ecosim_server.results.result_column import ColumnValue, ResultColumn
from ecosim_server.simulation.state.simulation_state import SimulationState


@dataclass(frozen=True)
class ResultTable:
    """Contains the results of a run, one row per step and one column per interface."""

    columns: tuple[ResultColumn, ...]
    # the end of each step, in UTC from PostgreSQL
    times: tuple[datetime, ...]
    rows: tuple[tuple[ColumnValue, ...], ...]
    state: SimulationState | None
    warnings: tuple[str, ...] = ()
    _left_out_inputs: tuple[ResultColumn, ...] = field(default=(), repr=False)

    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def values(self, column_name: str) -> list[ColumnValue]:
        positions = self._positions_of(names=[column_name])
        if len(positions) > 1:
            raise ValueError(f"{column_name} matches {len(positions)} columns. Use the name of one column, like {self.columns[positions[0]].name}.")
        return [row[positions[0]] for row in self.rows]

    def without_inputs(self) -> ResultTable:
        outputs = self._with_positions(positions=[position for position, column in enumerate(self.columns) if not column.is_input])
        return replace(outputs, _left_out_inputs=(*self._left_out_inputs, *(column for column in self.columns if column.is_input)))

    def select(self, names: Sequence[str]) -> ResultTable:
        """Returns the columns that match the names, in the order of the names."""
        return self._with_positions(positions=self._positions_of(names=names))

    def matches(self, name: str) -> bool:
        return bool(_positions_matching(columns=self.columns, name=name))

    def write_csv(self, file: str | Path) -> None:
        with Path(file).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["time", *self.column_names()])
            # the csv module writes None as an empty cell
            writer.writerows([time.isoformat(), *row] for time, row in zip(self.times, self.rows, strict=True))

    def to_data_frame(self) -> Any:
        """Returns a pandas DataFrame with the times as index."""
        try:
            import pandas
        except ImportError as error:
            raise ImportError('to_data_frame needs pandas. Install it with: pip install "ecosim-server[pandas]"') from error
        index = pandas.DatetimeIndex(data=list(self.times), name="time")
        return pandas.DataFrame(data=list(self.rows), index=index, columns=list(self.column_names()), dtype="float64")

    def _positions_of(self, names: Sequence[str]) -> list[int]:
        positions: list[int] = []
        for name in names:
            matching = _positions_matching(columns=self.columns, name=name)
            if not matching:
                raise ValueError(self._unknown_name_message(name=name))
            positions += [position for position in matching if position not in positions]
        return positions

    def _unknown_name_message(self, name: str) -> str:
        if _positions_matching(columns=self._left_out_inputs, name=name):
            return f"{name} is an input. Read the inputs with include_inputs=True."
        simulator_names = dict.fromkeys(column.simulator_name for column in self.columns)
        return f"The results have no column {name}.{did_you_mean(name=name, known_names=[*self.column_names(), *simulator_names])}"

    def _with_positions(self, positions: list[int]) -> ResultTable:
        return replace(
            self,
            columns=tuple(self.columns[position] for position in positions),
            rows=tuple(tuple(row[position] for position in positions) for row in self.rows),
        )


def _positions_matching(columns: Sequence[ResultColumn], name: str) -> list[int]:
    exact = [position for position, column in enumerate(columns) if column.matches(name=name)]
    # PostgreSQL stores the names in lower case
    return exact or [position for position, column in enumerate(columns) if column.matches(name=name.lower(), ignore_case=True)]
