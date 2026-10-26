from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_test_common.resources.config_files import config_file_path

# restoring a run turns the stored timestamps back into step numbers.
# without a time zone, a timestamp is read as local time and lands on the wrong step.


@pytest.fixture
def local_time_outside_utc(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="the local time zone cannot be changed on Windows")
@pytest.mark.usefixtures("local_time_outside_utc")
def test_a_timestamp_read_from_a_file_gives_the_step_it_was_written_for(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    config = SimulationConfig.of_config_file_and_params(config_file_path("simulation.json"), 100)
    repository = MeasurementRepositoryFile.create(tmp_path, simulator_name="house", communication_protocol=communication_protocol)

    repository.add((ProtocolInterfaceValue(name="T_room", value=293.15),), config.date_time_for_step(5))

    assert config.date_time_to_step(repository.all()[0].timestamp) == 5
