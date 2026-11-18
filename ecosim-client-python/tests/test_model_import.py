import json
import re
from pathlib import Path

import pytest
from ecosim_test_common.resources.resource_utils import python_room_config_path
from ecosim_test_common.test_data.python_models import DoublingModel

from ecosim_client_python.model_import import create_model, import_model_factory
from ecosim_client_python.python_config import PythonConfig


def test_a_module_next_to_the_ini_file_is_imported() -> None:
    room_directory = python_room_config_path().parent

    model = create_model(config=PythonConfig(module_name="room", class_name="Room", directory=room_directory))

    assert type(model).__module__ == "room"
    assert model.initialize() == {"temperature": 20.0}


def test_a_module_next_to_the_ini_file_comes_before_an_installed_module_of_the_same_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installed_packages = tmp_path / "site-packages"
    simulation_directory = tmp_path / "simulation"
    for directory in (installed_packages, simulation_directory):
        directory.mkdir()
        (directory / "shadowed_heater.py").write_text(f"class Heater:\n    found_in = {directory.name!r}\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(installed_packages))

    model_factory = import_model_factory(config=PythonConfig(module_name="shadowed_heater", class_name="Heater", directory=simulation_directory))

    assert model_factory().found_in == "simulation"


def test_an_installed_module_is_imported_by_its_full_name(tmp_path: Path) -> None:
    config = PythonConfig(module_name="ecosim_test_common.test_data.python_models", class_name="DoublingModel", directory=tmp_path)

    assert import_model_factory(config=config) is DoublingModel


def test_a_module_with_the_name_of_an_already_loaded_module_has_to_be_renamed(tmp_path: Path) -> None:
    (tmp_path / "json.py").touch()
    config = PythonConfig(module_name="json", class_name="Room", directory=tmp_path)
    expected_message = f"A module json is already loaded from {json.__file__}. Rename {tmp_path / 'json.py'} and change model in the ini file"

    with pytest.raises(ImportError, match=re.escape(expected_message)):
        import_model_factory(config=config)


def test_an_error_while_the_model_is_loaded_names_the_model_and_keeps_the_error(tmp_path: Path) -> None:
    (tmp_path / "cooler_dividing_by_zero.py").write_text("class Cooler:\n    def __init__(self):\n        self.share = 1 / 0\n", encoding="utf-8")
    config = PythonConfig(module_name="cooler_dividing_by_zero", class_name="Cooler", directory=tmp_path)

    with pytest.raises(RuntimeError, match=re.escape("The model cooler_dividing_by_zero:Cooler could not be loaded: division by zero")) as error_info:
        create_model(config=config)

    assert isinstance(error_info.value.__cause__, ZeroDivisionError)


def test_a_model_without_the_three_methods_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "boiler.py").write_text("class Boiler:\n    def initialize(self):\n        return {}\n", encoding="utf-8")
    config = PythonConfig(module_name="boiler", class_name="Boiler", directory=tmp_path)
    expected_message = "boiler:Boiler needs initialize(), do_step(inputs, current_simulation_time, step_size_in_seconds) and clear()"

    with pytest.raises(TypeError, match=re.escape(expected_message)):
        create_model(config=config)
