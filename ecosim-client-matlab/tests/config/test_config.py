import re
from pathlib import Path
from typing import Iterable

import pytest
from ecosim_common.config.config_parser import ConfigParser

from ecosim_client_matlab.matlab_config import MatlabConfig


def _matlab_config_with_scripts(directory: Path, script_folder: str, script_names: Iterable[str]) -> MatlabConfig:
    (directory / script_folder).mkdir()
    for script_name in script_names:
        (directory / script_folder / script_name).write_text("")
    ini_file = directory / "preferences.ini"
    ini_file.write_text(f"[matlab]\nscriptfolder={script_folder}\n")
    return MatlabConfig(config=ConfigParser(path=ini_file))


def test_a_relative_script_folder_is_resolved_against_the_ini(tmp_path: Path) -> None:
    config = _matlab_config_with_scripts(directory=tmp_path, script_folder="scripts", script_names=MatlabConfig.SCRIPT_NAMES)
    assert config.folder_path == tmp_path / "scripts"


@pytest.mark.parametrize("missing_script", MatlabConfig.SCRIPT_NAMES)
def test_a_missing_script_is_named_in_the_error(tmp_path: Path, missing_script: str) -> None:
    present_scripts = [name for name in MatlabConfig.SCRIPT_NAMES if name != missing_script]
    with pytest.raises(FileNotFoundError, match=re.escape(f"is missing {missing_script}")):
        _matlab_config_with_scripts(directory=tmp_path, script_folder="scripts", script_names=present_scripts)
