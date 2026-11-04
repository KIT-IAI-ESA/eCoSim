from datetime import datetime
from pathlib import Path

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from integration_tests.server_client.performance.tooling.performance_repository import PerformanceRepository


def test_protocol_date_and_machine_are_taken_from_the_file_name(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = PerformanceRepository.of(tmp_path / f"2026-11-04_090507_{communication_protocol.serialized}_local_my_laptop.jsonl")
    assert repository.communication_protocol == communication_protocol
    assert repository.date_of_test_run == datetime(2026, 11, 4, 9, 5, 7)
    assert repository.machine_name == "local_my_laptop"


@pytest.mark.parametrize("file_name", ["results.jsonl", "2026-11-04_090507_unknown_local_my_laptop.jsonl", "2026-11-04_090507_dask.jsonl"])
def test_a_file_name_not_in_the_format_date_time_protocol_machine_fails(tmp_path: Path, file_name: str) -> None:
    with pytest.raises(ValueError):
        PerformanceRepository.of(tmp_path / file_name)


def test_write_stores_the_measurement_with_protocol_and_machine_of_the_file(tmp_path: Path) -> None:
    repository = PerformanceRepository.of(tmp_path / f"2026-11-04_090507_{CommunicationProtocol.DASK.serialized}_local_my_laptop.jsonl")
    measurement = ServerTimeMeasurement(protocol=CommunicationProtocol.TCP_SOCKET)
    measurement.set_start(ServerTimeMeasurementType.SIMULATION_EXECUTION)
    measurement.set_end(ServerTimeMeasurementType.SIMULATION_EXECUTION)

    repository.write(measurement=measurement, test_name="test_a", total_time=2.5)

    [result] = repository.all()
    assert (result.test_name, result.total_time_in_seconds) == ("test_a", 2.5)
    assert (result.communication_protocol, result.machine) == (CommunicationProtocol.DASK, "local_my_laptop")
    assert result.execution_time_in_seconds is not None
    assert result.start_time_in_seconds is None
