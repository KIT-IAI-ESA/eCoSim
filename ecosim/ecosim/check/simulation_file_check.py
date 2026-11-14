from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecosim_common.tech.json.read_json_file import read_json_file
from ecosim_server.config.connection_check import connection_problems
from ecosim_server.config.simulation_config_keys import missing_key_problems, unknown_key_warnings

from ecosim.check.findings import Findings, problem_of
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class SimulationFileCheck:
    """simulation.json as JSON, with the checks that need nothing else."""

    # None if the file is not valid JSON
    raw_config: Any
    findings: Findings
    has_every_key: bool = False

    @staticmethod
    def of_file(file: Path, run_options: RunOptions) -> SimulationFileCheck:
        try:
            raw_config = read_json_file(file=file)
        except (OSError, ValueError) as error:
            return SimulationFileCheck(raw_config=None, findings=Findings(problems=[problem_of(error=error, file=file)]))
        missing = missing_key_problems(
            raw_config=raw_config,
            simulation_config_file=file,
            has_step_size_override=run_options.step_size_in_milliseconds is not None,
            # a check without a length checks a run of one step, see steps_for_the_check
            has_steps_override=run_options.steps is not None or not _has_steps(raw_config=raw_config),
        )
        if missing:
            return SimulationFileCheck(raw_config=raw_config, findings=Findings(problems=missing))
        return SimulationFileCheck(
            raw_config=raw_config,
            findings=Findings(
                problems=_connection_problems(raw_config=raw_config, file=file),
                warnings=unknown_key_warnings(raw_config=raw_config, simulation_config_file=file),
            ),
            has_every_key=True,
        )

    def can_be_loaded(self) -> bool:
        """Else the loader of the server would only repeat the problems found here."""
        return self.has_every_key and not self.findings.problems

    def has_steps(self) -> bool:
        return _has_steps(raw_config=self.raw_config)

    def steps_for_the_check(self, run_options: RunOptions) -> int | None:
        """None takes setup.steps, and a check without a length checks one step."""
        if run_options.steps is not None or self.has_steps():
            return run_options.steps
        return 1


def _has_steps(raw_config: Any) -> bool:
    return isinstance(raw_config, dict) and isinstance(raw_config.get("setup"), dict) and "steps" in raw_config["setup"]


def _connection_problems(raw_config: dict[str, Any], file: Path) -> list[str]:
    try:
        problems = connection_problems(raw_simulators=raw_config["simulators"], raw_logical_delays=raw_config["logical_delays"])
    except (TypeError, AttributeError, KeyError):
        # a value of the wrong type, which the loader of the server names
        return []
    return [f"{file}: {problem}" for problem in problems]
