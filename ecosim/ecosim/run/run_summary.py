from typing import assert_never

from ecosim_common.tech.datetime.readable_duration import readable_duration

from ecosim.run.local_run import RunOutcome
from ecosim.run.run_watch import RunEnd


def summary_lines(outcome: RunOutcome, results_location: str, restore_command: str, read_command: str) -> list[str]:
    duration = readable_duration(seconds=outcome.run_time_in_seconds)
    match outcome.end:
        case RunEnd.FINISHED:
            return [f"Finished after {duration}. Results: {results_location}", f"Read them with: {read_command}"]
        case RunEnd.FAILED:
            return [f"Failed after {duration}. The results so far: {results_location}"]
        case RunEnd.INTERRUPTED | RunEnd.TERMINATED:
            return [f"Stopped after {duration}. The results so far: {results_location}", f"Continue the run with: {restore_command}"]
        case _:
            assert_never(outcome.end)
