from pathlib import Path

from ecosim.check.checked_simulator import CheckedSimulator
from ecosim.report_lines import ecosim_program, length_line, simulator_lines
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.test_data.building_simulation import write_building_simulation


def test_the_simulator_lines_line_up_their_columns(tmp_path: Path) -> None:
    simulation = write_building_simulation(directory=tmp_path / "building")
    simulators = [
        CheckedSimulator(
            directory=SimulatorDirectory.of_ini_file(ini_file=simulation / "Modules" / name / "preferences.ini"),
            client_type=ClientType.FMU_2,
            input_count=inputs,
            output_count=outputs,
        )
        for name, inputs, outputs in (("house", 18, 6), ("occupancy", 0, 7))
    ]

    lines = simulator_lines(simulators=simulators)

    assert [line.replace(str(simulation), "building") for line in lines] == [
        "  house      FMI 2.0  building/Modules/house      18 inputs  6 outputs",
        "  occupancy  FMI 2.0  building/Modules/occupancy   0 inputs  7 outputs",
    ]


def test_the_length_line_shows_the_steps_the_step_size_and_the_simulated_period(tmp_path: Path) -> None:
    simulation = write_building_simulation(directory=tmp_path)
    simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=simulation / "server" / "simulation.json", steps=35_040)

    assert length_line(simulation_config=simulation_config) == "35,040 steps of 15 min, from 2023-01-01 00:00 to 2024-01-01 00:00 UTC."


def test_a_printed_command_starts_with_uv_run_when_uv_run_started_ecosim() -> None:
    assert ecosim_program(environment={"UV": "/usr/bin/uv"}) == ["uv", "run", "ecosim"]
