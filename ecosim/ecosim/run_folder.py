from __future__ import annotations

import filecmp
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# the start time, and a number for a second run in the same second
RUN_FOLDER_NAME = re.compile(r"(?P<start>\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d)(_(?P<number>\d+))?")


@dataclass(frozen=True)
class RunFolder:
    """The result files of one run, a copy of simulation.json, and logs/ with a log for each part."""

    path: Path

    @staticmethod
    def new_in(results: Path, start: datetime) -> RunFolder:
        # local time without colons, which Windows does not allow in a name
        name = f"{start:%Y-%m-%d_%H-%M-%S}"
        path, number = results / name, 2
        while path.exists():
            path, number = results / f"{name}_{number}", number + 1
        return RunFolder(path=path)

    @staticmethod
    def newest(results: Path) -> RunFolder | None:
        """The run folder with the latest start time in its name, since other names come from --results."""
        if not results.is_dir():
            return None
        named = {folder: match for folder in results.iterdir() if (match := RUN_FOLDER_NAME.fullmatch(folder.name)) is not None}
        run_folders = [folder for folder in named if RunFolder(path=folder).holds_a_run()]
        if not run_folders:
            return None
        return RunFolder(path=max(run_folders, key=lambda folder: (named[folder]["start"], int(named[folder]["number"] or 1))))

    @property
    def logs(self) -> Path:
        return self.path / "logs"

    @property
    def temporary_files(self) -> Path:
        # the FMUs a killed client extracted stay here instead of in the temporary folder of the system
        return self.path / "tmp"

    @property
    def simulation_config_copy(self) -> Path:
        return self.path / "simulation.json"

    def log_file_of(self, part_name: str) -> Path:
        return self.logs / f"{part_name}.log"

    def holds_a_run(self) -> bool:
        return (self.path / "simulation_state.jsonl").is_file() or self.simulation_config_copy.is_file()

    def create(self, simulation_config: Path, copies_the_simulation_config: bool) -> None:
        """The server copies simulation.json for results as files, so only a PostgreSQL run copies it here."""
        self.logs.mkdir(parents=True, exist_ok=True)
        if copies_the_simulation_config:
            shutil.copyfile(src=simulation_config, dst=self.simulation_config_copy)

    def has_changed(self, simulation_config: Path) -> bool:
        """Whether the simulation config differs from the one of the run, which a restore needs unchanged."""
        return self.simulation_config_copy.is_file() and not filecmp.cmp(simulation_config, self.simulation_config_copy, shallow=False)
