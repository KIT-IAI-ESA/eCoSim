from pathlib import Path

from ecosim_common.config.database_type import DatabaseType
from ecosim_server.run_summary import RunSummary
from tests.data.generate_postgres_name_config import generate_simulation_config
from tests.data.generate_server_config import generate_server_config


def _summary(
    failure_reason: str | None = None,
    completed_steps: int = 100,
    restored_steps: int = 0,
    step_time_in_seconds: float | None = 2.0,
    database_type: DatabaseType = DatabaseType.FILE,
    results_directory: Path = Path("results"),
) -> RunSummary:
    return RunSummary(
        failure_reason=failure_reason,
        completed_steps=completed_steps,
        restored_steps=restored_steps,
        step_time_in_seconds=step_time_in_seconds,
        simulation_config=generate_simulation_config(clients=[], steps=100, step_size_in_ms=900_000),
        database=generate_server_config(
            database_type=database_type,
            database_directory=results_directory,
            database_schema="temp_schema",
        ).database,
    )


def test_a_finished_run_names_its_steps_its_simulated_period_and_its_results(tmp_path: Path) -> None:
    summary = _summary(results_directory=tmp_path)

    assert summary.header() == "SIMULATION FINISHED"
    assert summary.value_pairs() == {
        "Steps": "100 of 100, in 2.0 s (50 steps/s)",
        "Simulated period": "2024-01-01 00:00 to 2024-01-02 01:00 UTC",
        "Results": f"files in {tmp_path}",
    }


def test_a_failed_run_says_why_and_how_to_continue_it(tmp_path: Path) -> None:
    summary = _summary(
        failure_reason="Lost client weather#weather while waiting for the response of step 37",
        completed_steps=37,
        results_directory=tmp_path,
    )

    assert summary.header() == "SIMULATION FAILED"
    assert summary.value_pairs() == {
        "Steps": "37 of 100, in 2.0 s (18 steps/s)",
        "Simulated period": "2024-01-01 00:00 to 2024-01-01 09:15 UTC",
        "Reason": "Lost client weather#weather while waiting for the response of step 37",
        "Results": f"files in {tmp_path}",
        "Continue the run": "start the server again with the same options and --restore-simulation-run, then the clients",
    }


def test_a_run_that_failed_before_its_first_step_names_no_results_and_no_restore() -> None:
    summary = _summary(failure_reason="stopped by Ctrl-C or a kill signal", completed_steps=0, step_time_in_seconds=None)

    assert summary.value_pairs() == {"Steps": "0 of 100", "Reason": "stopped by Ctrl-C or a kill signal"}


def test_the_speed_of_a_restored_run_counts_only_the_steps_of_this_run() -> None:
    summary = _summary(restored_steps=60, step_time_in_seconds=4.0)

    assert summary.value_pairs()["Steps"] == "100 of 100, 60 of them restored, in 4.0 s (10 steps/s)"


def test_postgres_results_name_the_database_its_server_and_the_schema() -> None:
    summary = _summary(database_type=DatabaseType.POSTGRES)

    assert summary.value_pairs()["Results"] == "PostgreSQL database sim_control on localhost:5432, schema temp_schema"
