from pathlib import Path

from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.results import ResultColumn, ResultTable
from ecosim_server.results.result_column import ColumnValue
from ecosim_server.simulation.state.simulation_state import SimulationState
from tests.results.stored_run import StoredRun


def write_results(directory: Path, steps: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    StoredRun.in_directory(directory=directory).write_files(directory=directory, steps=steps)
    return directory


def create_result_table(steps: int = 4, state: SimulationState | None = SimulationState.FINISHED) -> ResultTable:
    """Returns a house with a room temperature and the outdoor temperature as an input, in steps of 15 min."""
    return create_house_table_with(rows=tuple((290.0 + step, 270.0 - step) for step in range(steps)), state=state)


def create_house_table_with(
    rows: tuple[tuple[ColumnValue, ColumnValue], ...],
    state: SimulationState | None = SimulationState.FINISHED,
) -> ResultTable:
    columns = (
        ResultColumn(simulator_name="house", interface_name="T_room", interface_type=InterfaceType.OUTPUT, unit="K"),
        ResultColumn(simulator_name="house", interface_name="T_out", interface_type=InterfaceType.INPUT, unit="K"),
    )
    return ResultTable(columns=columns, simulation_times=tuple(StoredRun.time_of(step) for step in range(len(rows))), rows=rows, state=state)
