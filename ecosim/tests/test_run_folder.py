from datetime import datetime
from pathlib import Path

from ecosim.run_folder import RunFolder

START = datetime(year=2026, month=11, day=16, hour=9, minute=30, second=12)


def test_every_run_gets_a_new_folder_named_after_its_start_time(tmp_path: Path) -> None:
    assert RunFolder.new_in(results=tmp_path, start=START).path == tmp_path / "2026-11-16_09-30-12"


def test_a_second_run_in_the_same_second_gets_a_folder_of_its_own(tmp_path: Path) -> None:
    (tmp_path / "2026-11-16_09-30-12").mkdir()
    (tmp_path / "2026-11-16_09-30-12_2").mkdir()

    assert RunFolder.new_in(results=tmp_path, start=START).path == tmp_path / "2026-11-16_09-30-12_3"


def test_a_restore_continues_the_newest_folder_that_holds_a_run(tmp_path: Path) -> None:
    for name in ("2026-11-15_08-00-00", "2026-11-16_09-30-12"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "simulation_state.jsonl").touch()
    (tmp_path / "2026-11-17_10-00-00").mkdir()

    assert RunFolder.newest(results=tmp_path) == RunFolder(path=tmp_path / "2026-11-16_09-30-12")


def test_a_restore_goes_by_the_start_time_and_number_of_a_folder_and_not_by_another_name(tmp_path: Path) -> None:
    for name in ("2026-11-16_09-30-12_2", "2026-11-16_09-30-12_10", "my-first-try"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "simulation.json").touch()

    assert RunFolder.newest(results=tmp_path) == RunFolder(path=tmp_path / "2026-11-16_09-30-12_10")


def test_a_simulation_without_results_has_no_run_to_restore(tmp_path: Path) -> None:
    assert RunFolder.newest(results=tmp_path / "results") is None


def test_a_run_folder_keeps_a_copy_of_the_simulation_config_for_postgres_results(tmp_path: Path) -> None:
    simulation_config = tmp_path / "simulation.json"
    simulation_config.write_text('{"setup": {}}', encoding="utf-8")
    run_folder = RunFolder(path=tmp_path / "results" / "run")

    run_folder.create(simulation_config=simulation_config, copies_the_simulation_config=True)
    unchanged = run_folder.has_changed(simulation_config=simulation_config)
    simulation_config.write_text('{"setup": {"steps": 3}}', encoding="utf-8")

    assert (run_folder.logs.is_dir(), run_folder.holds_a_run(), unchanged, run_folder.has_changed(simulation_config=simulation_config)) == (
        True,
        True,
        False,
        True,
    )
