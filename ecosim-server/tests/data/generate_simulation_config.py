from __future__ import annotations

from pathlib import Path

from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources.config_files import config_file_path

HOUSE = ClientID(model_name="house", simulator_name="house")
WEATHER = ClientID(model_name="weather", simulator_name="weather")


def generate_simulation_config_from_file(
    simulation_json: Path = config_file_path("simulation.json"),
) -> SimulationConfig:
    return SimulationConfig.of_config_file_and_params(
        simulation_config_file=simulation_json,
        steps=100,
    )
