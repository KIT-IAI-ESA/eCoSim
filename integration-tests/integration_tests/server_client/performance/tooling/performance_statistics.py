from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, Iterable, Iterator, List, Tuple

from ecosim_common.tech.logger.global_logger import GlobalLogger

from integration_tests.server_client.performance.tooling.performance_setup import (
    format_seconds,
)
from integration_tests.server_client.performance.tooling.time_statistic import TimeStatistic


@dataclass(frozen=True)
class PerformanceStatistics:
    _COLUMNS: ClassVar[Tuple[str, ...]] = ("time", "expected", "actual", "tolerance", "deviation")
    _SEPARATOR: ClassVar[str] = " | "

    statistics: Tuple[TimeStatistic, ...] = ()

    @classmethod
    def of(cls, statistics: Iterable[TimeStatistic]) -> PerformanceStatistics:
        return cls(statistics=tuple(statistics))

    def __iter__(self) -> Iterator[TimeStatistic]:
        return iter(self.statistics)

    def __len__(self) -> int:
        return len(self.statistics)

    def __add__(self, other: PerformanceStatistics) -> PerformanceStatistics:
        return PerformanceStatistics(statistics=self.statistics + other.statistics)

    def filter_slower_than_expected(self) -> PerformanceStatistics:
        return PerformanceStatistics.of(statistic for statistic in self.statistics if statistic.is_too_slow())

    def describe(self) -> str:
        return "; ".join(statistic.describe() for statistic in self.statistics)

    def grouped_for_output(self) -> Dict[str, List[str]]:
        values: Dict[str, List[str]] = {}
        for statistic in self.statistics:
            values.setdefault(f"{statistic.test_name} ({statistic.communication_protocol.serialized})", []).append(statistic.describe())
        return values

    def as_table(self) -> List[str]:
        rows = [self._COLUMNS, *(self._row_of(statistic) for statistic in self.statistics)]
        widths = [max(len(row[column]) for row in rows) for column in range(len(self._COLUMNS))]
        lines = [self._line_of(row, widths) for row in rows]
        lines.insert(1, "-+-".join("-" * width for width in widths))
        return lines

    def print_summary_to_log_and_file(self, file_path: Path) -> None:
        lines = GlobalLogger.format_values_to_lines(
            header="Performance Statistics",
            value_pairs=self.grouped_for_output(),
        )
        for line in lines:
            GlobalLogger.logger.info("%s", line)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _row_of(statistic: TimeStatistic) -> Tuple[str, ...]:
        deviation = "-" if statistic.deviation is None else f"{statistic.deviation:+.1%}"
        return (
            statistic.measurement_name,
            format_seconds(statistic.expected),
            format_seconds(statistic.current),
            f"{statistic.tolerance:.1%}",
            deviation,
        )

    @classmethod
    def _line_of(cls, row: Tuple[str, ...], widths: List[int]) -> str:
        cells = [row[0].ljust(widths[0]), *(cell.rjust(width) for cell, width in zip(row[1:], widths[1:]))]
        return cls._SEPARATOR.join(cells)
