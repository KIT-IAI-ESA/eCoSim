from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from ecosim_server.config.simulation_config import SimulationConfig


def _load(tmp_path: Path, start_date: str) -> SimulationConfig:
    file = tmp_path / "simulation.json"
    file.write_text(json.dumps({"simulators": [], "logical_delays": [], "setup": {"delta_t": 1000, "start_date": start_date}}))
    return SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)


@pytest.mark.parametrize("start_date", ["2024-03-17T13:59:07", "2024-03-17T13:59:07.123", "2024-03-17"])
def test_a_start_date_without_an_offset_is_rejected_with_its_value(tmp_path: Path, start_date: str) -> None:
    with pytest.raises(RuntimeError, match=f"start_date '{start_date}' has no time zone offset"):
        _load(tmp_path, start_date=start_date)


def test_a_start_date_in_utc_is_accepted(tmp_path: Path) -> None:
    expected = datetime(year=2024, month=3, day=17, hour=13, minute=59, second=7, tzinfo=timezone.utc)

    assert _load(tmp_path, start_date="2024-03-17T13:59:07Z").start_date == expected


def test_a_start_date_with_an_offset_is_accepted(tmp_path: Path) -> None:
    expected = datetime(year=2024, month=3, day=17, hour=13, minute=59, second=7, tzinfo=timezone(timedelta(hours=1)))

    assert _load(tmp_path, start_date="2024-03-17T13:59:07+01:00").start_date == expected
