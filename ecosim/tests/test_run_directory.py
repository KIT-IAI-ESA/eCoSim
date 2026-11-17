from datetime import datetime
from pathlib import Path

from ecosim.run_directory import RunDirectory

START = datetime(year=2026, month=11, day=16, hour=9, minute=30, second=12)


def test_every_run_gets_a_new_directory_named_after_its_start_time(tmp_path: Path) -> None:
    assert RunDirectory.new_in(results=tmp_path, start=START).path == tmp_path / "2026-11-16_09-30-12"


def test_a_second_run_in_the_same_second_gets_its_own_directory(tmp_path: Path) -> None:
    (tmp_path / "2026-11-16_09-30-12").mkdir()
    (tmp_path / "2026-11-16_09-30-12_2").mkdir()

    assert RunDirectory.new_in(results=tmp_path, start=START).path == tmp_path / "2026-11-16_09-30-12_3"


def test_a_restore_continues_the_newest_directory_with_a_run(tmp_path: Path) -> None:
    for name in ("2026-11-15_08-00-00", "2026-11-16_09-30-12"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "simulation_state.jsonl").touch()
    (tmp_path / "2026-11-17_10-00-00").mkdir()

    assert RunDirectory.newest(results=tmp_path) == RunDirectory(path=tmp_path / "2026-11-16_09-30-12")


def test_the_newest_run_is_found_by_start_time_and_number_not_by_another_name(tmp_path: Path) -> None:
    for name in ("2026-11-16_09-30-12_2", "2026-11-16_09-30-12_10", "my-first-try"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "simulation.json").touch()

    assert RunDirectory.newest(results=tmp_path) == RunDirectory(path=tmp_path / "2026-11-16_09-30-12_10")


def test_a_simulation_without_results_has_no_run_to_restore(tmp_path: Path) -> None:
    assert RunDirectory.newest(results=tmp_path / "results") is None


def test_a_run_directory_keeps_a_copy_of_the_simulation_config_for_postgres_results(tmp_path: Path) -> None:
    simulation_config = tmp_path / "simulation.json"
    simulation_config.write_text('{"setup": {}}', encoding="utf-8")
    run_directory = RunDirectory(path=tmp_path / "results" / "run")

    run_directory.create(simulation_config=simulation_config, copies_the_simulation_config=True)

    assert run_directory.simulation_config_copy.read_text(encoding="utf-8") == '{"setup": {}}'


def test_a_simulation_config_that_changed_since_the_run_started_is_noticed(tmp_path: Path) -> None:
    simulation_config = tmp_path / "simulation.json"
    simulation_config.write_text('{"setup": {}}', encoding="utf-8")
    run_directory = RunDirectory(path=tmp_path / "results" / "run")
    run_directory.create(simulation_config=simulation_config, copies_the_simulation_config=True)
    changed_before = run_directory.has_changed(simulation_config=simulation_config)

    simulation_config.write_text('{"setup": {"steps": 3}}', encoding="utf-8")

    assert not changed_before
    assert run_directory.has_changed(simulation_config=simulation_config)
