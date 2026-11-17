from pathlib import Path

from ecosim_common.client.config.interface_file_keys import repeated_name_warnings, unknown_key_warnings

FMC_FILE = Path("Modules/house/house.fmc")


def test_the_keys_of_the_example_files_are_not_warned() -> None:
    raw_interfaces = {
        "fmu-file": "house.fmu",
        "modeldescription": "modelDescription.xml",
        "inputs": [{"name": "T_out", "unit": "K", "description": "", "required": "true", "type": "Input", "connected_to": []}],
        "outputs": [{"name": "T_indoor", "unit": "K"}],
    }

    assert unknown_key_warnings(raw_interfaces=raw_interfaces, fmc_file=FMC_FILE) == []


def test_a_misspelled_key_is_warned_once_with_the_number_of_interfaces_and_the_closest_key() -> None:
    raw_interfaces = {
        "input": [],
        "inputs": [{"name": "T_out", "requird": "true"}, {"name": "wind", "requird": "true"}],
        "outputs": [{"name": "T_indoor", "unti": "K"}],
    }

    assert unknown_key_warnings(raw_interfaces=raw_interfaces, fmc_file=FMC_FILE) == [
        f'{FMC_FILE} has the unknown key "input". Did you mean inputs?',
        f'{FMC_FILE}: 2 inputs have the unknown key "requird". Did you mean required?',
        f'{FMC_FILE}: 1 output has the unknown key "unti". Did you mean unit?',
    ]


def test_a_name_that_a_list_has_twice_is_warned() -> None:
    raw_interfaces = {"inputs": [{"name": "T_indoor"}], "outputs": [{"name": "T_indoor"}, {"name": "T_indoor"}, {"name": "CO2"}]}

    assert repeated_name_warnings(raw_interfaces=raw_interfaces, fmc_file=FMC_FILE) == [f"{FMC_FILE} lists the output T_indoor 2 times."]
