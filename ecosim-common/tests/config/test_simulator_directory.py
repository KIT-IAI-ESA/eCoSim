import re
from pathlib import Path

import pytest
from ecosim_common.client.config.simulator_directory import SimulatorDirectory, SimulatorDirectorySearch
from ecosim_common.config.client_id import ClientID
from ecosim_test_common.test_data.generate_simulator_directory import write_simulator_directory


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


def test_two_directories_for_one_simulator_fail_naming_both_directories(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    write_simulator_directory(directory=tmp_path / "first_house", client_id=house, model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "second_house", client_id=house, model_file="house.fmu")

    with pytest.raises(RuntimeError, match="are both for simulator") as error:
        SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[house])

    assert str(tmp_path / "first_house") in str(error.value)
    assert str(tmp_path / "second_house") in str(error.value)


def test_every_directory_whose_ini_file_cannot_be_read_is_named(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    weather = ClientID(model_name="weather", simulator_name="weather")
    write_simulator_directory(directory=tmp_path / "house", client_id=house, model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "weather", client_id=weather, model_file="weather.fmu")
    house_ini = tmp_path / "house" / "preferences.ini"
    house_ini.write_text(house_ini.read_text().replace("model_name=house\n", ""))
    weather_ini = tmp_path / "weather" / "preferences.ini"
    weather_ini.write_text(weather_ini.read_text().replace("type=fmu", "type=fmu4"))

    with pytest.raises(RuntimeError) as error:
        SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[house, weather])

    assert str(house_ini) in str(error.value)
    assert str(weather_ini) in str(error.value)


def test_the_search_lists_every_unusable_directory_with_the_reason(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    occupancy = ClientID(model_name="occupancy", simulator_name="occupancy")
    weather = ClientID(model_name="weather", simulator_name="weather")
    heating = ClientID(model_name="heating", simulator_name="heating")
    write_simulator_directory(directory=tmp_path / "house", client_id=house, model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "first_occupancy", client_id=occupancy, model_file="occupancy.fmu")
    write_simulator_directory(directory=tmp_path / "second_occupancy", client_id=occupancy, model_file="occupancy.fmu")
    write_simulator_directory(directory=tmp_path / "weather", client_id=weather, model_file=None)
    write_simulator_directory(directory=tmp_path / "hous", client_id=ClientID(model_name="house", simulator_name="hous"), model_file="house.fmu")
    write_simulator_directory(directory=tmp_path / "copies", client_id=heating, model_file="heating.fmu")
    (tmp_path / "copies" / "copy.ini").write_text((tmp_path / "copies" / "preferences.ini").read_text())
    (tmp_path / "no_model_name").mkdir()
    (tmp_path / "no_model_name" / "preferences.ini").write_text("[simulator]\nsimulator_name=heating\n")

    search = SimulatorDirectorySearch.of(simulators_directory=tmp_path, client_ids=[house, occupancy, weather, heating])

    assert list(search.found) == [house]
    assert [directory.path for directory in search.unconfigured] == [tmp_path / "hous"]
    assert {client_id: sorted(directory.path for directory in directories) for client_id, directories in search.shared.items()} == {
        occupancy: [tmp_path / "first_occupancy", tmp_path / "second_occupancy"],
    }
    assert "copy.ini" in search.unreadable[tmp_path / "copies"]
    assert "model_name" in search.unreadable[tmp_path / "no_model_name"]
    assert [directory.path for directory in search.without_model] == [tmp_path / "weather"]
    assert search.missing == [heating]


def test_the_reason_for_an_ini_file_that_cannot_be_read_names_the_file(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    for directory in ["unknown_type", "no_section", "utf_16"]:
        write_simulator_directory(directory=tmp_path / directory, client_id=house, model_file="house.fmu")
    unknown_type_ini = tmp_path / "unknown_type" / "preferences.ini"
    unknown_type_ini.write_text(unknown_type_ini.read_text().replace("type=fmu", "type=fmu4"))
    no_section_ini = tmp_path / "no_section" / "preferences.ini"
    no_section_ini.write_text(no_section_ini.read_text().removeprefix("[simulator]\n"))
    utf_16_ini = tmp_path / "utf_16" / "preferences.ini"
    utf_16_ini.write_text(utf_16_ini.read_text(), encoding="utf-16")

    search = SimulatorDirectorySearch.of(simulators_directory=tmp_path, client_ids=[house])

    named_directories = sorted(path.name for path, reason in search.unreadable.items() if str(path / "preferences.ini") in reason)
    assert named_directories == ["no_section", "unknown_type", "utf_16"]


def test_the_model_files_are_the_python_fmu_and_matlab_files_of_the_directory_in_name_order(tmp_path: Path) -> None:
    house = ClientID(model_name="house", simulator_name="house")
    write_simulator_directory(directory=tmp_path / "house", client_id=house, model_file="house.fmu")
    for other_file in ["model.py", "setup.m", "notes.txt"]:
        (tmp_path / "house" / other_file).touch()

    simulator_directory = SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[house])[house]

    assert [model_file.name for model_file in simulator_directory.model_files()] == ["house.fmu", "model.py", "setup.m"]


def test_a_python_model_named_in_the_ini_needs_no_model_file_in_the_directory(tmp_path: Path) -> None:
    room = ClientID(model_name="room", simulator_name="room")
    write_simulator_directory(
        directory=tmp_path / "room",
        client_id=room,
        model_file=None,
        extra_ini_text="[python]\nmodel=building_models.room:Room\n",
    )

    simulator_directories = SimulatorDirectory.find_for_simulators(simulators_directory=tmp_path, client_ids=[room])

    assert simulator_directories[room].path == tmp_path / "room"
