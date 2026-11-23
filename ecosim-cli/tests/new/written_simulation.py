from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ecosim.new.new_command import main


@dataclass(frozen=True)
class WrittenSimulation:
    directory: Path
    exit_code: int
    report_lines: list[str]

    @staticmethod
    def of_fmu_files(directory: Path, fmu_files: Sequence[Path], options: Sequence[str] = ()) -> WrittenSimulation:
        report = io.StringIO()
        with contextlib.redirect_stdout(report):
            exit_code = main(passed_arguments=[str(directory), *(str(fmu_file) for fmu_file in fmu_files), *options])
        return WrittenSimulation(directory=directory, exit_code=exit_code, report_lines=report.getvalue().splitlines())
