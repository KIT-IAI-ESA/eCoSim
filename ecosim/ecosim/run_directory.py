from __future__ import annotations

import filecmp
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RunDirectory:
    path: Path

    @staticmethod
    def new_in(results: Path, start: datetime) -> RunDirectory:
        # Windows allows no colons in a name
        name = f"{start:%Y-%m-%d_%H-%M-%S}"
        path, number = results / name, 2
        while path.exists():
            path, number = results / f"{name}_{number}", number + 1
        return RunDirectory(path=path)

    @staticmethod
    def newest(results: Path) -> RunDirectory | None:
        if not results.is_dir():
            return None
        # the start time, and a number for a second run in the same second
        name_pattern = re.compile(r"(?P<start>\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d)(_(?P<number>\d+))?")
        matches = {directory: match for directory in results.iterdir() if (match := name_pattern.fullmatch(directory.name)) is not None}
        run_directories = [directory for directory in matches if RunDirectory(path=directory).has_a_run()]
        if not run_directories:
            return None
        return RunDirectory(path=max(run_directories, key=lambda directory: (matches[directory]["start"], int(matches[directory]["number"] or 1))))

    @property
    def logs(self) -> Path:
        return self.path / "logs"

    @property
    def temporary_files(self) -> Path:
        # a killed client leaves its extracted FMU behind
        return self.path / "tmp"

    @property
    def simulation_config_copy(self) -> Path:
        return self.path / "simulation.json"

    @property
    def simulation_state_file(self) -> Path:
        return self.path / "simulation_state.jsonl"

    def log_file_of(self, process_name: str) -> Path:
        return self.logs / f"{process_name}.log"

    def has_a_run(self) -> bool:
        return self.simulation_state_file.is_file() or self.simulation_config_copy.is_file()

    def create(self, simulation_config: Path, copies_the_simulation_config: bool) -> None:
        self.logs.mkdir(parents=True, exist_ok=True)
        if copies_the_simulation_config:
            shutil.copyfile(src=simulation_config, dst=self.simulation_config_copy)

    def has_changed(self, simulation_config: Path) -> bool:
        return self.simulation_config_copy.is_file() and not filecmp.cmp(f1=simulation_config, f2=self.simulation_config_copy, shallow=False)
