import re
from pathlib import Path

import pytest
from ecosim_common.config.config_parser import ConfigParser

from ecosim_client_python.python_config import PythonConfig


def _python_config_of(directory: Path, model: str) -> PythonConfig:
    ini_file = directory / "preferences.ini"
    ini_file.write_text(f"[python]\nmodel = {model}\n", encoding="utf-8")
    return PythonConfig.of(config_parser=ConfigParser(path=ini_file))


def test_the_model_names_a_module_and_a_class_and_the_folder_of_the_ini_file(tmp_path: Path) -> None:
    config = _python_config_of(directory=tmp_path, model="room : Room")

    assert (config.module_name, config.class_name, config.folder) == ("room", "Room", tmp_path)


@pytest.mark.parametrize("model", ["room", "room:", ":Room", ".room:Room"])
def test_a_model_that_does_not_name_a_module_and_a_class_says_how_to_write_it(tmp_path: Path, model: str) -> None:
    expected_message = f"{tmp_path / 'preferences.ini'}: model in [python] has to name a module and a class, like model = room:Room, not '{model}'"

    with pytest.raises(ValueError, match=re.escape(expected_message)):
        _python_config_of(directory=tmp_path, model=model)
