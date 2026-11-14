"""The overview that ecosim results prints: the run, then the minimum, mean and maximum of every column."""

import statistics
from collections import Counter
from datetime import datetime, timedelta

from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_common.tech.datetime.readable_period import readable_period
from ecosim_common.tech.readable_count import readable_count
from ecosim_server.results import ResultTable
from ecosim_server.results.result_column import ColumnValue
from ecosim_server.simulation.state.simulation_state import SimulationState

STATE_TEXTS = {
    SimulationState.FINISHED: "finished",
    SimulationState.FAILED: "failed",
    SimulationState.READY: "not finished",
    SimulationState.STARTED: "not finished",
    SimulationState.NOT_READY: "not started",
}
# a run that stores no end can still run, or it was killed before it could store one
NOT_ENDED = (SimulationState.READY, SimulationState.STARTED)
NUMBER_WIDTH = 14


def overview_lines(table: ResultTable, source: str, left_out_inputs: int) -> list[str]:
    """left_out_inputs: how many inputs the table leaves out, so the overview can say how to show them."""
    step_size = _step_size_of(times=table.simulation_times)
    state = "state unknown" if table.state is None else STATE_TEXTS[table.state]
    step_count = readable_count(count=len(table.simulation_times), noun="step")
    steps = step_count if step_size is None else f"{step_count} of {readable_duration(seconds=step_size)}"
    not_ended = ". It is still running, or it was stopped." if table.state in NOT_ENDED else ""
    return [
        f"Results:     {source}",
        f"Run:         {state}, {steps}{not_ended}",
        f"Simulated:   {_period_text(times=table.simulation_times, step_size=step_size)}",
        f"Simulators:  {', '.join(dict.fromkeys(column.simulator_name for column in table.columns))}",
        f"Columns:     {_columns_text(table=table, left_out_inputs=left_out_inputs)}",
        "",
        *_statistics_lines(table=table),
    ]


def _step_size_of(times: tuple[datetime, ...]) -> float | None:
    """The most common time between two rows in seconds, None for fewer than two rows."""
    differences = Counter(later - earlier for earlier, later in zip(times, times[1:]))
    return differences.most_common(1)[0][0].total_seconds() if differences else None


def _period_text(times: tuple[datetime, ...], step_size: float | None) -> str:
    if not times:
        return "nothing"
    if step_size is None:
        # one row does not tell the step size, so only the end of the step is known
        return f"the step that ends at {times[0].isoformat()}"
    # the time of a row is the end of its step
    return readable_period(start=times[0] - timedelta(seconds=step_size), end=times[-1])


def _columns_text(table: ResultTable, left_out_inputs: int) -> str:
    if any(column.interface_type is None for column in table.columns):
        # without the run's simulation.json the reader cannot tell them apart
        return f"{readable_count(count=len(table.columns), noun='column')}, inputs and outputs together"
    inputs = sum(column.is_input for column in table.columns)
    outputs = len(table.columns) - inputs
    shown = " and ".join(
        [
            *([readable_count(count=outputs, noun="output")] if outputs or not inputs else []),
            *([readable_count(count=inputs, noun="input")] if inputs else []),
        ],
    )
    verb = "is" if left_out_inputs == 1 else "are"
    return shown + (f", {readable_count(count=left_out_inputs, noun='input')} {verb} left out (add --inputs)" if left_out_inputs else "")


def _statistics_lines(table: ResultTable) -> list[str]:
    header = ("Column", "Unit", "".join(f"{title:>{NUMBER_WIDTH}}" for title in ("Minimum", "Mean", "Maximum")))
    rows = [
        header,
        *(
            (column.name, column.unit, _statistics_text(values=[row[position] for row in table.rows]))
            for position, column in enumerate(table.columns)
        ),
    ]
    name_width = max(len(name) for name, _, _ in rows)
    # a unit column only when the simulation config names a unit
    unit_width = max(len(unit) for _, unit, _ in rows) if any(column.unit for column in table.columns) else 0
    return [f"{name:<{name_width}}  " + (f"{unit:<{unit_width}}  " if unit_width else "") + numbers for name, unit, numbers in rows]


def _statistics_text(values: list[ColumnValue]) -> str:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return "".join(f"{'-':>{NUMBER_WIDTH}}" for _ in range(3))
    return "".join(f"{number:>{NUMBER_WIDTH},.6g}" for number in (min(numbers), statistics.fmean(numbers), max(numbers)))
