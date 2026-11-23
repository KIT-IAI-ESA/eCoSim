import re
from pathlib import Path

import fmpy
import pytest
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.test_data.building_simulation import write_building_simulation
from ecosim_test_common.test_data.generate_changed_fmu import generate_fmu_without_binaries_for

from tests.simulation_changes import add_room_simulator, change_json_file, check_of, interface_named, replace_in_file


@pytest.fixture
def simulation(tmp_path: Path) -> Path:
    return write_building_simulation(directory=tmp_path / "building")


def test_the_building_simulation_has_no_problems(simulation: Path) -> None:
    check = check_of(simulation)

    assert check.findings.problems == []
    assert [(simulator.name, simulator.input_count, simulator.output_count) for simulator in check.simulators] == [
        ("house", 18, 6),
        ("occupancy", 0, 7),
        ("weather", 0, 11),
    ]


def test_a_misspelled_simulator_name_in_an_ini_file_is_one_problem(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "house" / "preferences.ini", old="simulator_name=house", new="simulator_name=hous")

    assert check_of(simulation).findings.problems == [
        f"{simulation}/modules/house/preferences.ini: simulator_name is 'hous', "
        + f"but {simulation}/server/simulation.json has no simulator 'hous'. Did you mean house?",
    ]


def test_a_simulator_without_its_directory_is_not_counted(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "house" / "preferences.ini", old="simulator_name=house", new="simulator_name=hous")

    assert check_of(simulation).simulator_count == 2


def test_a_misspelled_input_in_the_simulation_config_suggests_the_input_of_the_fmu(simulation: Path) -> None:
    change_json_file(
        file=simulation / "server" / "simulation.json",
        change=lambda config: interface_named(simulator=config["simulators"][0], name="weatherBus_TDryBul").update(name="weatherBus_TDryBull"),
    )

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{simulation}/modules/house: ")
    assert problem.endswith("Did you mean weatherBus_TDryBul?")


def test_a_misspelled_output_in_the_fmc_file_is_one_finding_with_the_fmu_variable(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "house" / "house.fmc", old='"T_indoor"', new='"T_indor"')

    check = check_of(simulation)

    [finding] = [finding for finding in [*check.findings.problems, *check.findings.warnings] if "T_indor" in finding]
    assert finding.startswith(f"{simulation}/modules/house/house.fmc: ")
    assert finding.endswith("Did you mean T_indoor?")


def test_every_problem_is_listed_not_only_the_first(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "house" / "house.fmc", old='"T_indoor"', new='"T_indor"')
    replace_in_file(file=simulation / "modules" / "occupancy" / "preferences.ini", old="fmu_file=", new="fmufile=")
    replace_in_file(file=simulation / "modules" / "weather" / "preferences.ini", old="model_name=weather", new="model_name=Weather")

    problems = check_of(simulation).findings.problems

    assert [problem.split(": ")[0].split(" has ")[0] for problem in problems] == [
        f"{simulation}/modules/weather/preferences.ini",
        f"{simulation}/modules/house/house.fmc",
        f"{simulation}/modules/occupancy/preferences.ini",
    ]


def test_a_wrong_setup_value_does_not_hide_the_problems_of_the_simulators(simulation: Path) -> None:
    change_json_file(file=simulation / "server" / "simulation.json", change=lambda config: config["setup"].update(steps="0"))
    replace_in_file(file=simulation / "modules" / "weather" / "preferences.ini", old="model_name=weather", new="model_name=Weather")

    setup_problem, simulator_problem = check_of(simulation).findings.problems

    assert setup_problem.startswith(f"{simulation}/server/simulation.json: setup.steps")
    assert simulator_problem == (
        f"{simulation}/modules/weather/preferences.ini: model_name is 'Weather', "
        + f"but simulator weather in {simulation}/server/simulation.json has the model weather."
    )


def test_invalid_json_is_a_problem_with_the_line_and_the_column(simulation: Path) -> None:
    replace_in_file(file=simulation / "server" / "simulation.json", old='"setup": {', new='"setup" {')

    [problem] = check_of(simulation).findings.problems

    assert re.fullmatch(rf"{simulation}/server/simulation.json .* line \d+,? column \d+.*", problem)


def test_a_missing_logical_delays_key_is_a_problem(simulation: Path) -> None:
    change_json_file(file=simulation / "server" / "simulation.json", change=lambda config: config.pop("logical_delays"))

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f'{simulation}/server/simulation.json has no key "logical_delays".')


def test_a_misspelled_start_date_is_a_warning_and_not_a_problem(simulation: Path) -> None:
    change_json_file(
        file=simulation / "server" / "simulation.json",
        change=lambda config: config["setup"].update({"start-date": config["setup"].pop("start_date")}),
    )

    check = check_of(simulation)

    assert check.findings.problems == []
    assert len([warning for warning in check.findings.warnings if '"start-date"' in warning]) == 1


def test_a_section_written_in_another_case_is_suggested(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "weather" / "preferences.ini", old="[simulator]", new="[Simulator]")

    [problem] = check_of(simulation).findings.problems

    assert problem.endswith("Did you mean [simulator] instead of [Simulator]?")


def test_a_misspelled_key_of_a_client_config_is_suggested(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "weather" / "preferences.ini", old="fmu_file=", new="fmufile=")

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{simulation}/modules/weather/preferences.ini")
    assert problem.endswith("Did you mean fmu_file instead of fmufile?")


def test_a_directory_without_its_model_is_a_problem(simulation: Path) -> None:
    (simulation / "modules" / "weather" / "weather.fmu").unlink()

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{simulation}/modules/weather has no model")


def test_an_fmu_that_cannot_be_read_is_a_problem_and_the_check_goes_on(simulation: Path) -> None:
    house_fmu = simulation / "modules" / "house" / "house.fmu"
    house_fmu.write_text("not a zip file", encoding="utf-8")
    replace_in_file(file=simulation / "modules" / "weather" / "preferences.ini", old="fmu_file=", new="fmufile=")

    problem_of_the_fmu, problem_of_the_weather = check_of(simulation).findings.problems

    assert problem_of_the_fmu == f"{house_fmu} cannot be read: File is not a zip file"
    assert problem_of_the_weather.startswith(f"{simulation}/modules/weather/preferences.ini")


def test_a_simulator_directory_without_an_ini_file_is_a_problem(simulation: Path) -> None:
    (simulation / "modules" / "weather" / "preferences.ini").unlink()

    assert check_of(simulation).findings.problems == [
        f"{simulation}/modules/weather has no ini file. Add an ini file whose simulator_name is weather and whose model_name is weather.",
    ]


def test_an_fmu_without_a_binary_for_this_platform_is_a_problem(simulation: Path, tmp_path: Path) -> None:
    weather_fmu = simulation / "modules" / "weather" / "weather.fmu"
    generate_fmu_without_binaries_for(fmu_file=weather_fmu, directory=tmp_path, platform=fmpy.platform).replace(weather_fmu)

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{weather_fmu} has no binary for this platform ({fmpy.platform}), only for ")


def test_a_start_value_the_fmu_cannot_take_is_a_problem(simulation: Path) -> None:
    with (simulation / "modules" / "house" / "preferences.ini").open("a", encoding="utf-8") as ini_file:
        ini_file.write("\n[start_values]\nU_wal = 0.3\n")

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{simulation}/modules/house/preferences.ini: [start_values] U_wal")


def test_a_start_value_of_an_input_connected_by_the_simulation_config_is_a_warning(simulation: Path) -> None:
    change_json_file(
        file=simulation / "modules" / "house" / "house.fmc",
        change=lambda fmc: fmc.update(inputs=[interface for interface in fmc["inputs"] if interface["name"] != "weatherBus_TDryBul"]),
    )
    with (simulation / "modules" / "house" / "preferences.ini").open("a", encoding="utf-8") as ini_file:
        ini_file.write("\n[start_values]\nweatherBus_TDryBul = 280\n")

    check = check_of(simulation)

    assert check.findings.problems == []
    assert (
        f"{simulation}/modules/house/preferences.ini: the start value of weatherBus_TDryBul has no effect. "
        + "The simulation config connects this input."
    ) in check.findings.warnings


def test_a_misspelled_database_key_is_suggested_for_postgres_results(simulation: Path) -> None:
    replace_in_file(file=simulation / "server" / "preferences.ini", old="username=", new="usrname=")

    [problem] = check_of(simulation, "--database-type", "postgres").findings.problems

    assert problem.startswith(f"{simulation}/server/preferences.ini")
    assert problem.endswith("Did you mean username instead of usrname?")


def test_the_python_model_of_a_simulator_is_imported_by_the_check(simulation: Path) -> None:
    add_room_simulator(simulation=simulation)

    check = check_of(simulation)

    assert check.findings.problems == []
    assert [simulator.name for simulator in check.simulators] == ["house", "occupancy", "weather", "room"]


def test_a_misspelled_class_of_a_python_model_is_a_problem_of_its_ini_file(simulation: Path) -> None:
    room = add_room_simulator(simulation=simulation)
    replace_in_file(file=room / "preferences.ini", old="model=room:Room", new="model=room:Rom")

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{room}/preferences.ini: ")
    assert "Rom" in problem


def test_a_python_model_that_imports_a_package_that_is_not_installed_is_a_problem(simulation: Path) -> None:
    room = add_room_simulator(simulation=simulation)
    room_module = room / "room.py"
    room_module.write_text(f"import gridmodels_not_installed\n{room_module.read_text(encoding='utf-8')}", encoding="utf-8")

    [problem] = check_of(simulation).findings.problems

    assert problem.startswith(f"{room}/preferences.ini: ")
    assert "gridmodels_not_installed" in problem


def test_a_matlab_model_is_not_checked_without_the_matlab_client(simulation: Path) -> None:
    room = add_room_simulator(simulation=simulation)
    (room / "room.py").rename(room / "setup.m")
    replace_in_file(file=room / "preferences.ini", old="[python]\nmodel=room:Room", new="[matlab]\nscriptfolder=.")

    check = check_of(simulation)

    assert check.findings.problems == []
    assert f"{room}: [matlab] was not checked. ecosim-client-matlab is not installed." in check.findings.warnings


def test_a_pyro5_object_that_nothing_listens_on_is_a_warning(simulation: Path) -> None:
    room = add_room_simulator(simulation=simulation)
    port = get_free_port()
    replace_in_file(file=room / "preferences.ini", old="[python]\nmodel=room:Room", new=f"[pyro]\npyro_host=localhost\npyro_port={port}")

    check = check_of(simulation)

    assert check.findings.problems == []
    assert (
        f"{room}/preferences.ini: nothing listens on pyro_host localhost and pyro_port {port}. Start the Pyro5 object before the run. "
        + "If it runs already, set pyro_host and pyro_port to the address it listens on."
    ) in check.findings.warnings


def test_a_client_port_that_differs_from_the_server_port_is_only_a_warning(simulation: Path) -> None:
    replace_in_file(file=simulation / "modules" / "weather" / "preferences.ini", old="port=1234", new="port=1235")

    check = check_of(simulation)

    assert check.findings.problems == []
    assert (
        f"{simulation}/modules/weather/preferences.ini: port in [server] is 1235, but {simulation}/server/preferences.ini has port 1234. "
        + "That only matters for a client started manually."
    ) in check.findings.warnings


def test_an_unreadable_server_config_is_one_problem_without_a_port_warning(simulation: Path) -> None:
    server_config = simulation / "server" / "preferences.ini"
    replace_in_file(file=server_config, old="[database]\n", new="[database]\ntype file\n")

    check = check_of(simulation)

    assert len(check.findings.problems) == 1
    assert [warning for warning in check.findings.warnings if str(server_config) in warning] == []


@pytest.mark.parametrize("steps_option, steps", [([], 96), (["--steps", "10"], 10), (["--duration", "1h"], 4)])
def test_the_length_of_the_run_comes_from_the_options_or_else_the_setup(simulation: Path, steps_option: list[str], steps: int) -> None:
    change_json_file(file=simulation / "server" / "simulation.json", change=lambda config: config["setup"].update(steps=96))

    simulation_config = check_of(simulation, *steps_option).simulation_config

    assert simulation_config is not None and simulation_config.steps == steps
