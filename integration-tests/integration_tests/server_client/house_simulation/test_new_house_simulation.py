from pathlib import Path

import pytest
from ecosim.new.new_command import main
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData

from integration_tests.server_client.house_simulation.house_simulation import HouseSimulation


def _write_house_simulation(directory: Path) -> Path:
    fmu_files = [str(HouseSimulationData.fmu_file(module)) for module in HouseSimulationData.MODULES]
    # the recorded run connects these inputs to outputs with other names
    connections = [
        "--connect=house.dir_sol_iradiance=weather.dir_sol_irradiance",
        "--connect=house.heating_heatExchanger_control_signal=heating.heating_control_signal",
        "--connect=house.vetnilation_valve_control_signal=ventilation.ventilation_valve_control_signal",
        "--connect=heating.T_room=house.room_temperature",
        "--connect=ventilation.T_room=house.room_temperature",
    ]
    # the FMUs start T_room at 0 K, the recorded run at 293.15 K
    delays = ["--logical-delay=heating.T_room=293.15", "--logical-delay=ventilation.T_room=293.15"]
    exit_code = main(passed_arguments=[str(directory), *fmu_files, "--step-size=1min", f"--steps={HouseSimulationData.STEPS}", *connections, *delays])
    assert exit_code == ShutdownManager.SUCCESS_EXIT_CODE
    return directory


@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()
def test_a_simulation_written_by_ecosim_new_reproduces_the_recorded_house_results(
    communication_protocol: CommunicationProtocol,
    tmp_path: Path,
) -> None:
    simulation_directory = _write_house_simulation(directory=tmp_path / "house_simulation")
    simulation = HouseSimulation.of(
        communication_protocol=communication_protocol,
        host="localhost",
        port=get_free_port(),
        simulation_config_file=simulation_directory / "server" / "simulation.json",
        client_config_file=lambda module: simulation_directory / "modules" / module / "preferences.ini",
    )

    simulation.run()

    for module in HouseSimulationData.MODULES:
        recorded, expected = simulation.recorded_rows(module), HouseSimulationData.expected_rows(module)
        for step, (recorded_row, expected_row) in enumerate(zip(recorded, expected, strict=True), start=1):
            assert {name: recorded_row[name] for name in expected_row} == pytest.approx(expected_row), f"{module}, step {step}"
