import shutil
import zipfile
from pathlib import Path

import pytest
from ecosim.new.simulation_model import SimulationModel
from ecosim_test_common.resources.resource_utils import fmu2_model_path


def _fmu_copy(file: Path) -> Path:
    file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src=fmu2_model_path(), dst=file)
    return file


def test_a_model_is_named_after_its_fmu_file_with_an_underscore_for_other_characters(tmp_path: Path) -> None:
    models = SimulationModel.of_arguments(arguments=[str(_fmu_copy(file=tmp_path / "heat pump.v2.fmu"))])

    assert [model.name for model in models] == ["heat_pump_v2"]


def test_a_name_before_the_equals_sign_names_the_model(tmp_path: Path) -> None:
    fmu_file = _fmu_copy(file=tmp_path / "house.fmu")

    models = SimulationModel.of_arguments(arguments=[str(fmu_file), f"house2={fmu_file}"])

    assert [(model.name, model.interfaces.fmu_file) for model in models] == [("house", fmu_file), ("house2", fmu_file)]


def test_a_folder_adds_each_fmu_in_it_in_name_order(tmp_path: Path) -> None:
    for name in ("weather", "house", "occupancy"):
        _fmu_copy(file=tmp_path / "models" / f"{name}.fmu")
    _fmu_copy(file=tmp_path / "models" / "old" / "heating.fmu")

    models = SimulationModel.of_arguments(arguments=[str(tmp_path / "models")])

    assert [model.name for model in models] == ["house", "occupancy", "weather"]


def test_two_models_whose_names_differ_only_in_case_are_refused(tmp_path: Path) -> None:
    arguments = [str(_fmu_copy(file=tmp_path / "a" / "house.fmu")), str(_fmu_copy(file=tmp_path / "b" / "House.fmu"))]

    with pytest.raises(ValueError) as error:
        SimulationModel.of_arguments(arguments=arguments)

    assert str(error.value) == f"2 models get the name house: {', '.join(arguments)}. Name one of them, like house_2={arguments[1]}"


def test_a_missing_fmu_file_names_the_closest_fmu_next_to_it(tmp_path: Path) -> None:
    _fmu_copy(file=tmp_path / "house.fmu")

    with pytest.raises(ValueError) as error:
        SimulationModel.of_arguments(arguments=[str(tmp_path / "hous.fmu")])

    assert str(error.value) == f"There is no file {tmp_path / 'hous.fmu'}. Did you mean house.fmu?"


def test_a_file_that_is_no_fmu_is_refused_with_the_reason_of_fmpy(tmp_path: Path) -> None:
    (tmp_path / "broken.fmu").write_text("not a zip file", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        SimulationModel.of_arguments(arguments=[str(tmp_path / "broken.fmu")])

    assert str(error.value) == f"{tmp_path / 'broken.fmu'} cannot be read as an FMU: File is not a zip file"


def test_a_name_that_windows_keeps_for_a_device_is_refused(tmp_path: Path) -> None:
    fmu_file = _fmu_copy(file=tmp_path / "con.fmu")

    with pytest.raises(ValueError) as error:
        SimulationModel.of_arguments(arguments=[str(fmu_file)])

    assert str(error.value) == f"'con' cannot be a model name, since Windows keeps it for a device. Name the model, like con_model={fmu_file}"


def test_a_folder_after_the_equals_sign_is_refused_since_a_name_takes_one_fmu_file(tmp_path: Path) -> None:
    _fmu_copy(file=tmp_path / "models" / "house.fmu")

    with pytest.raises(ValueError) as error:
        SimulationModel.of_arguments(arguments=[f"house={tmp_path / 'models'}"])

    assert str(error.value) == f"{tmp_path / 'models'} is a folder, but NAME=FILE takes one .fmu file."


def test_a_zip_file_without_a_model_description_is_refused_with_the_missing_file(tmp_path: Path) -> None:
    with zipfile.ZipFile(tmp_path / "empty.fmu", mode="w") as fmu:
        fmu.writestr(zinfo_or_arcname="readme.txt", data="no model here")

    with pytest.raises(ValueError) as error:
        SimulationModel.of_arguments(arguments=[str(tmp_path / "empty.fmu")])

    assert str(error.value) == f"{tmp_path / 'empty.fmu'} cannot be read as an FMU: it has no modelDescription.xml."
