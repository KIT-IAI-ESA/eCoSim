from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_input, create_logical_delay, create_output, create_simulator


def load_config(tmp_path: Path, *simulators: dict[str, Any], logical_delays: list[dict[str, Any]] | None = None) -> SimulationConfig:
    file = config_file(tmp_path, *simulators, logical_delays=logical_delays)
    return SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)


def error_of(tmp_path: Path, *simulators: dict[str, Any], logical_delays: list[dict[str, Any]] | None = None) -> str:
    with pytest.raises(RuntimeError) as error:
        load_config(tmp_path, *simulators, logical_delays=logical_delays)
    return str(error.value)


def single_delay_file(directory: Path, delay: int, start_value: Any) -> Path:
    return config_file(
        directory,
        create_simulator("sender", create_output("sent")),
        create_simulator("receiver", create_input("delayed", simulator="0", interface="sent", delay_path=["1"])),
        logical_delays=[create_logical_delay("receiver", "delayed", delay=delay, start_value=start_value)],
    )
