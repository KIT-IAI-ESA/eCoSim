import json
from pathlib import Path
from typing import Any

import pytest
from ecosim_common.client.config.client_config import SimpleClientConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.config.config_parser import ConfigParser
from ecosim_test_common.resources.resource_utils import fmu3_model_path
from ecosim_test_common.test_data.building_simulation import BUILDING_MODULES

from tests.new.written_simulation import WrittenSimulation

# the outputs of the weather FMU have units
FMU_FILES = [fmu3_model_path(), BUILDING_MODULES / "weather" / "weather.fmu"]


@pytest.fixture(scope="module")
def simulation(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("new") / "simulation"
    return WrittenSimulation.of_fmu_files(directory=directory, fmu_files=FMU_FILES, options=["--port", "4321"]).directory


def _json_of(file: Path) -> Any:
    return json.loads(file.read_text(encoding="utf-8"))


def test_the_server_config_has_the_port_and_its_own_results_directory(simulation: Path) -> None:
    server_config = ConfigParser(simulation / "server" / "preferences.ini")

    assert server_config.get_section(section="server") == {"host": "localhost", "port": "4321"}
    assert server_config.get_section(section="database") == {"type": "file", "directory": "results/manual"}


def test_a_client_config_reads_back_with_the_port_and_the_client_of_its_fmi_version(simulation: Path) -> None:
    client_config = SimpleClientConfig.of_config_parser(config_parser=ConfigParser(simulation / "Modules" / "StateSpace" / "preferences.ini"))

    assert (client_config.server_config().server_address.port, client_config.type()) == (4321, ClientType.FMU_3)


def test_the_written_files_keep_the_unit_and_the_description_of_the_fmu(simulation: Path) -> None:
    fmc_entry = _json_of(file=simulation / "Modules" / "weather" / "weather.fmc")["outputs"][0]
    weather = _json_of(file=simulation / "server" / "simulation.json")["simulators"][1]

    assert fmc_entry == {"name": "weatherBus.HDifHor", "unit": "W/m2", "description": "Diffuse horizontal solar irradiation"}
    assert weather["interfaces"][0] == {**fmc_entry, "type": "Output"}


def test_results_in_postgres_get_a_database_section_without_a_password(tmp_path: Path) -> None:
    simulation = WrittenSimulation.of_fmu_files(directory=tmp_path / "simulation", fmu_files=FMU_FILES, options=["--database-type", "postgres"])

    database_section = ConfigParser(simulation.directory / "server" / "preferences.ini").get_section(section="database")

    assert database_section == {"type": "postgres", "server": "localhost", "port": "5432", "username": "", "ssl": "false"}
