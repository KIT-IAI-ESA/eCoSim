import json
import re
from pathlib import Path

import pytest
from ecosim_test_common.resources.resource_utils import python_room_config_path
from ecosim_test_common.test_data.python_models import DoublingModel

from ecosim_client_python.model_import import import_model_factory
from ecosim_client_python.python_config import PythonConfig


def test_a_module_next_to_the_ini_file_is_imported() -> None:
    room_directory = python_room_config_path().parent

    model_factory = import_model_factory(config=PythonConfig(module_name="room", class_name="Room", directory=room_directory))

    assert model_factory.__module__ == "room"
    assert model_factory().initialize() == {"temperature": 20.0}


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


def test_a_missing_module_shows_the_directory_it_was_looked_for_in(tmp_path: Path) -> None:
    config = PythonConfig(module_name="no_such_model", class_name="Room", directory=tmp_path)

    with pytest.raises(ModuleNotFoundError, match=re.escape(f"No module no_such_model in {tmp_path}, and none is installed")):
        import_model_factory(config=config)


def test_a_misspelled_module_suggests_a_module_of_the_directory(tmp_path: Path) -> None:
    (tmp_path / "radiator.py").touch()
    config = PythonConfig(module_name="radiatr", class_name="Radiator", directory=tmp_path)

    with pytest.raises(ModuleNotFoundError, match=re.escape(f"No module radiatr in {tmp_path}, and none is installed. Did you mean radiator?")):
        import_model_factory(config=config)


def test_a_module_written_with_py_says_to_leave_it_out(tmp_path: Path) -> None:
    (tmp_path / "boiler.py").write_text("class Boiler:\n    pass\n", encoding="utf-8")
    config = PythonConfig(module_name="boiler.py", class_name="Boiler", directory=tmp_path)
    expected_message = "model in [python] needs the module without .py. Use model = boiler:Boiler, not 'boiler.py:Boiler'"

    with pytest.raises(ModuleNotFoundError, match=re.escape(expected_message)):
        import_model_factory(config=config)


def test_a_package_the_model_imports_but_is_missing_is_shown(tmp_path: Path) -> None:
    (tmp_path / "grid_with_a_missing_package.py").write_text("import no_such_package\n", encoding="utf-8")
    config = PythonConfig(module_name="grid_with_a_missing_package", class_name="Grid", directory=tmp_path)
    expected_message = (
        "no_such_package is not installed in the Python environment of this client. The model grid_with_a_missing_package:Grid imports it"
    )

    with pytest.raises(ModuleNotFoundError, match=re.escape(expected_message)):
        import_model_factory(config=config)


def test_a_missing_class_suggests_a_close_name() -> None:
    config = PythonConfig(module_name="room", class_name="Rom", directory=python_room_config_path().parent)

    with pytest.raises(AttributeError, match=re.escape("room.py has no Rom. Did you mean Room?")):
        import_model_factory(config=config)


def test_a_module_with_the_name_of_an_already_loaded_module_has_to_be_renamed(tmp_path: Path) -> None:
    (tmp_path / "json.py").touch()
    config = PythonConfig(module_name="json", class_name="Room", directory=tmp_path)
    expected_message = f"A module json is already loaded from {json.__file__}. Rename {tmp_path / 'json.py'} and change model in the ini file"

    with pytest.raises(ImportError, match=re.escape(expected_message)):
        import_model_factory(config=config)


def test_a_model_that_is_not_a_class_is_rejected(tmp_path: Path) -> None:
    config = PythonConfig(module_name="string", class_name="ascii_letters", directory=tmp_path)

    with pytest.raises(TypeError, match=re.escape("string:ascii_letters is not a class. Its type is str")):
        import_model_factory(config=config)
