from datetime import datetime, timedelta, timezone
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_server.results import ResultColumn, ResultTable
from ecosim_server.results.result_column import ColumnValue
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_input, create_output, create_simulator

START_DATE = datetime(year=2023, month=1, day=1, tzinfo=timezone.utc)
STEP_SIZE = timedelta(minutes=15)


def write_results(folder: Path, steps: int) -> Path:
    """A finished run of a weather with T_out and a house with T_room that gets T_out as an input, as the server writes it."""
    folder.mkdir(parents=True, exist_ok=True)
    config_file(
        folder,
        create_simulator("weather", create_output("T_out")),
        create_simulator("house", create_input("T_out_in", simulator="0", interface="T_out"), create_output("T_room")),
    )
    protocol = CommunicationProtocol.TCP_SOCKET
    for simulator_name, interface_names in (("weather", ("T_out",)), ("house", ("T_room", "T_out_in"))):
        repository = MeasurementRepositoryFile.create(directory=folder, simulator_name=simulator_name, communication_protocol=protocol)
        for step in range(steps):
            values = tuple(ProtocolInterfaceValue(name=name, value=_value_of(interface_name=name, step=step)) for name in interface_names)
            repository.add(values=values, timestamp=START_DATE + (step + 1) * STEP_SIZE)
    SimulationStateRepositoryFile.create(directory=folder, communication_protocol=protocol).update(SimulationState.FINISHED)
    return folder


def _value_of(interface_name: str, step: int) -> float:
    # the house is 20 K warmer than the weather
    return 290.0 + step if interface_name == "T_room" else 270.0 + step


def create_result_table(steps: int = 4, state: SimulationState | None = SimulationState.FINISHED) -> ResultTable:
    """A house with a room temperature in K and the outdoor temperature it gets as an input, in steps of 15 min."""
    return create_house_table_with(rows=tuple((290.0 + step, 270.0 - step) for step in range(steps)), state=state)


def create_house_table_with(
    rows: tuple[tuple[ColumnValue, ColumnValue], ...],
    state: SimulationState | None = SimulationState.FINISHED,
) -> ResultTable:
    """The table of create_result_table with these rows of the room temperature and the outdoor temperature."""
    columns = (
        ResultColumn(simulator_name="house", interface_name="T_room", interface_type=InterfaceType.OUTPUT, unit="K"),
        ResultColumn(simulator_name="house", interface_name="T_out", interface_type=InterfaceType.INPUT, unit="K"),
    )
    simulation_times = tuple(START_DATE + (step + 1) * STEP_SIZE for step in range(len(rows)))
    return ResultTable(columns=columns, simulation_times=simulation_times, rows=rows, state=state)
