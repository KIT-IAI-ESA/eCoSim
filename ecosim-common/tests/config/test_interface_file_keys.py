import json
import logging
from pathlib import Path

import pytest
from ecosim_common.client.config.client_config import ClientInterfaceConfig, SimulatorConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.interface_file_keys import repeated_name_warnings, unknown_key_warnings

FMC_FILE = Path("Modules/house/house.fmc")


def test_the_documented_keys_nothing_reads_are_not_warned() -> None:
    raw_interfaces = {
        "fmu-file": "house.fmu",
        "modeldescription": "modelDescription.xml",
        "inputs": [{"name": "T_out", "unit": "K", "description": "", "required": "true", "type": "Input", "connected_to": []}],
        "outputs": [{"name": "T_indoor", "unit": "K"}],
    }

    assert unknown_key_warnings(raw_interfaces=raw_interfaces, fmc_file=FMC_FILE) == []


def test_a_misspelt_key_is_warned_once_with_the_number_of_interfaces_and_the_closest_key() -> None:
    raw_interfaces = {"input": [], "inputs": [{"name": "T_out", "requird": "true"}, {"name": "wind", "requird": "true"}]}

    assert unknown_key_warnings(raw_interfaces=raw_interfaces, fmc_file=FMC_FILE) == [
        f'{FMC_FILE} has the key "input", which nothing reads. Did you mean inputs?',
        f'{FMC_FILE}: 2 inputs have the key "requird", which nothing reads. Did you mean required?',
    ]


def test_a_name_that_a_list_has_twice_is_warned() -> None:
    raw_interfaces = {"inputs": [{"name": "T_indoor"}], "outputs": [{"name": "T_indoor"}, {"name": "T_indoor"}, {"name": "CO2"}]}

    assert repeated_name_warnings(raw_interfaces=raw_interfaces, fmc_file=FMC_FILE) == [f"{FMC_FILE} lists the output T_indoor 2 times."]


def test_the_client_logs_a_warning_for_a_key_of_the_fmc_file_that_nothing_reads(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "house.fmc").write_text(json.dumps({"outputs": [{"name": "T_indoor", "unti": "K"}]}), encoding="utf-8")
    simulator_config = SimulatorConfig(simulator_name="house", model_name="house", fmc_file="house.fmc", type=ClientType.FMU_2)

    ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=tmp_path)

    assert [(record.levelno, record.getMessage()) for record in caplog.records if record.name == "ClientConfig"] == [
        (logging.WARNING, f'{tmp_path / "house.fmc"}: 1 output has the key "unti", which nothing reads. Did you mean unit?'),
    ]
