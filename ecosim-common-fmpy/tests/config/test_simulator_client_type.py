import shutil
from pathlib import Path

import pytest
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory
from ecosim_common.config.client_id import ClientID
from ecosim_common_fmpy.config.simulator_client_type import client_type_of, client_type_of_fmi_version
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path
from ecosim_test_common.test_data.generate_simulator_directory import write_simulator_directory

MODEL = ClientID(model_name="model", simulator_name="model")


@pytest.mark.parametrize(("fmu_file", "client_type"), [(fmu2_model_path(), ClientType.FMU_2), (fmu3_model_path(), ClientType.FMU_3)])
def test_an_fmu_directory_gets_the_client_of_its_fmi_version(tmp_path: Path, fmu_file: Path, client_type: ClientType) -> None:
    ini_file = write_simulator_directory(directory=tmp_path / "model", client_id=MODEL, model_file=None)
    shutil.copy(fmu_file, ini_file.parent)

    assert client_type_of(simulator_directory=SimulatorDirectory.of_ini_file(ini_file=ini_file)) == client_type


@pytest.mark.parametrize(("script", "client_type"), [("setup.m", ClientType.Matlab), ("model.py", ClientType.Pyro5)])
def test_a_directory_of_scripts_gets_the_matlab_or_the_pyro5_client(tmp_path: Path, script: str, client_type: ClientType) -> None:
    ini_file = write_simulator_directory(directory=tmp_path / "model", client_id=MODEL, model_file=script)

    assert client_type_of(simulator_directory=SimulatorDirectory.of_ini_file(ini_file=ini_file)) == client_type


def test_a_python_model_named_in_the_ini_gets_the_python_client_whatever_files_lie_next_to_it(tmp_path: Path) -> None:
    ini_file = write_simulator_directory(
        directory=tmp_path / "room",
        client_id=MODEL,
        model_file="helper.py",
        extra_ini_text="[python]\nmodel=room:Room\n",
    )
    shutil.copy(fmu2_model_path(), ini_file.parent)

    assert client_type_of(simulator_directory=SimulatorDirectory.of_ini_file(ini_file=ini_file)) == ClientType.Python


def test_model_files_of_two_kinds_are_refused_naming_both(tmp_path: Path) -> None:
    ini_file = write_simulator_directory(directory=tmp_path / "house", client_id=MODEL, model_file="helper.py")
    shutil.copy(fmu2_model_path(), ini_file.parent / "house.fmu")

    with pytest.raises(ValueError, match="different kinds: helper.py, house.fmu"):
        client_type_of(simulator_directory=SimulatorDirectory.of_ini_file(ini_file=ini_file))


def test_two_fmus_in_one_directory_are_refused_naming_both(tmp_path: Path) -> None:
    ini_file = write_simulator_directory(directory=tmp_path / "house", client_id=MODEL, model_file=None)
    shutil.copy(fmu2_model_path(), ini_file.parent / "house.fmu")
    shutil.copy(fmu2_model_path(), ini_file.parent / "house_copy.fmu")

    with pytest.raises(ValueError, match="several FMUs: house.fmu, house_copy.fmu"):
        client_type_of(simulator_directory=SimulatorDirectory.of_ini_file(ini_file=ini_file))


def test_a_folder_without_a_model_is_refused_saying_what_a_model_is(tmp_path: Path) -> None:
    ini_file = write_simulator_directory(directory=tmp_path / "house", client_id=MODEL, model_file=None)

    with pytest.raises(ValueError, match=r"house has no model\. Put an \.fmu, \.m or \.py file in it, or write model = <module>:<class>"):
        client_type_of(simulator_directory=SimulatorDirectory.of_ini_file(ini_file=ini_file))


def test_an_fmu_of_another_fmi_version_is_refused_naming_the_file() -> None:
    with pytest.raises(ValueError, match="old.fmu is FMI 1.0"):
        client_type_of_fmi_version(fmi_version="1.0", fmu_file=Path("old.fmu"))
