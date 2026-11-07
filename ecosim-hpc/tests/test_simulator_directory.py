import re
from pathlib import Path

import pytest
from ecosim_common.config.client_id import ClientID
from ecosim_hpc.simulator_directory import SimulatorDirectory


def write_simulator_directory(directory: Path, client_id: ClientID, model_file: str | None) -> None:
    directory.mkdir()
    (directory / "preferences.ini").write_text(
        f"[simulator]\nsimulator_name={client_id.simulator_name}\nmodel_name={client_id.model_name}\nfmc_file=[model.fmc]\ntype=fmu\n",
    )
    if model_file is not None:
        (directory / model_file).touch()


def test_two_simulators_of_one_model_each_get_their_own_directory(tmp_path: Path) -> None:
    first_house = ClientID(model_name="house", simulator_name="first_house")
    second_house = ClientID(model_name="house", simulator_name="second_house")
    write_simulator_directory(directory=tmp_path / "first", client_id=first_house, model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "second", client_id=second_house, model_file="house.fmu")

    simulator_directories = SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[first_house, second_house])

    assert simulator_directories[first_house].path == tmp_path / "first"
    assert simulator_directories[second_house].path == tmp_path / "second"


def test_several_ini_files_in_one_directory_fail_naming_the_directory(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    write_simulator_directory(directory=tmp_path / "house", client_id=house, model_file="house.fmu")
    (tmp_path / "house" / "copy.ini").write_text((tmp_path / "house" / "preferences.ini").read_text())

    with pytest.raises(RuntimeError, match=re.escape(str(tmp_path / "house"))):
        SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[house])


def test_two_directories_for_one_simulator_fail_naming_the_simulator(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    write_simulator_directory(directory=tmp_path / "first_house", client_id=house, model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "second_house", client_id=house, model_file="house.fmu")

    with pytest.raises(RuntimeError, match=re.escape(str(house))):
        SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[house])


def test_every_configured_simulator_without_a_directory_or_a_model_file_is_named(tmp_path: Path) -> None:
    """One directory to start, one without a model file, one naming another simulator of its model, and one simulator without a directory."""
    house = ClientID(model_name="house", simulator_name="house")
    occupancy = ClientID(model_name="occupancy", simulator_name="occupancy")
    weather = ClientID(model_name="weather", simulator_name="weather")
    heating = ClientID(model_name="heating", simulator_name="heating")
    other_weather = ClientID(model_name="weather", simulator_name="other_weather")
    write_simulator_directory(directory=tmp_path / "house", client_id=house, model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "occupancy", client_id=occupancy, model_file=None)
    write_simulator_directory(directory=tmp_path / "weather", client_id=other_weather, model_file="weather.fmu")

    with pytest.raises(RuntimeError) as error:
        SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[house, occupancy, weather, heating])

    named_simulators = [client_id for client_id in [house, occupancy, weather, heating] if str(client_id) in str(error.value)]
    assert named_simulators == [occupancy, weather, heating]
