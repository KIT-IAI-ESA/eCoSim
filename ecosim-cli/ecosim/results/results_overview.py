import statistics
from collections import Counter
from datetime import datetime, timedelta
from typing import assert_never

from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_common.tech.datetime.readable_period import readable_period
from ecosim_common.tech.readable_count import readable_count
from ecosim_server.results import ResultTable
from ecosim_server.results.result_column import ColumnValue
from ecosim_server.simulation.state.simulation_state import SimulationState

NUMBER_WIDTH = 14


def overview_lines(table: ResultTable, source: str, left_out_inputs: int) -> list[str]:
    step_size = _step_size_of(times=table.simulation_times)
    step_count = readable_count(count=len(table.simulation_times), noun="step")
    steps = step_count if step_size is None else f"{step_count} of {readable_duration(seconds=step_size)}"
    not_ended = ". It is still running, or it was stopped." if table.state in (SimulationState.READY, SimulationState.STARTED) else ""
    return [
        f"Results:     {source}",
        f"Run:         {_state_text(state=table.state)}, {steps}{not_ended}",
        f"Simulated:   {_period_text(times=table.simulation_times, step_size=step_size)}",
        f"Simulators:  {', '.join(dict.fromkeys(column.simulator_name for column in table.columns))}",
        f"Columns:     {_columns_text(table=table, left_out_inputs=left_out_inputs)}",
        "",
        *_statistics_lines(table=table),
    ]


def _state_text(state: SimulationState | None) -> str:
    match state:
        case None:
            return "state unknown"
        case SimulationState.FINISHED:
            return "finished"
        case SimulationState.FAILED:
            return "failed"
        case SimulationState.READY | SimulationState.STARTED:
            return "not finished"
        case SimulationState.NOT_READY:
            return "not started"
        case _:
            assert_never(state)


def _step_size_of(times: tuple[datetime, ...]) -> float | None:
    """Returns the most common time between two rows in seconds."""
    differences = Counter(later - earlier for earlier, later in zip(times, times[1:]))
    return differences.most_common(1)[0][0].total_seconds() if differences else None


def _period_text(times: tuple[datetime, ...], step_size: float | None) -> str:
    if not times:
        return "nothing"
    if step_size is None:
        return f"the step that ends at {times[0].isoformat()}"
    # the time of a row is the end of its step
    return readable_period(start=times[0] - timedelta(seconds=step_size), end=times[-1])


def _columns_text(table: ResultTable, left_out_inputs: int) -> str:
    if any(column.interface_type is None for column in table.columns):
        # only simulation.json tells inputs from outputs
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
    unit_width = max(len(unit) for _, unit, _ in rows) if any(column.unit for column in table.columns) else 0
    return [f"{name:<{name_width}}  " + (f"{unit:<{unit_width}}  " if unit_width else "") + numbers for name, unit, numbers in rows]


def _statistics_text(values: list[ColumnValue]) -> str:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return "".join(f"{'-':>{NUMBER_WIDTH}}" for _ in range(3))
    return "".join(f"{number:>{NUMBER_WIDTH},.6g}" for number in (min(numbers), statistics.fmean(numbers), max(numbers)))
