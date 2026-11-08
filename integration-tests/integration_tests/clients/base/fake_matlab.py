import io
from dataclasses import dataclass, field
from typing import Any, ClassVar


class FakeMatlabExecutionError(Exception):
    """Raised like 'matlab.engine.MatlabExecutionError' when a script fails."""


@dataclass
class FakeMatlabEngine:
    """
    Stands in for 'matlab.engine.MatlabEngine', which needs a Matlab installation.

    'step' doubles the input 'u' into the output 'y' and reports the 'client_time' it was called with as 'time',
    so a test can see which simulation time the client hands to its model.
    """

    STEP_OUTPUT: ClassVar[str] = "printed by step.m"
    STEP_ERROR_OUTPUT: ClassVar[str] = "warned by step.m"
    FINISHING_ERROR_OUTPUT: ClassVar[str] = "error reported by finishing.m"

    fails_on_finishing: bool = False
    workspace: dict[str, Any] = field(default_factory=dict)
    paths: list[str] = field(default_factory=list)
    is_shut_down: bool = False

    def addpath(self, path: str) -> None:
        self.paths.append(path)

    def setup(self, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None:
        self.workspace.update(y=0.0, time=0.0)

    def step(self, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None:
        self.workspace.update(y=2 * self.workspace["u"], time=self.workspace["client_time"])
        stdout.write(f"{FakeMatlabEngine.STEP_OUTPUT}\n")
        stderr.write(f"{FakeMatlabEngine.STEP_ERROR_OUTPUT}\n")

    def finishing(self, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None:
        if self.fails_on_finishing:
            stderr.write(f"{FakeMatlabEngine.FINISHING_ERROR_OUTPUT}\n")
            raise FakeMatlabExecutionError("finishing.m failed")

    def quit(self) -> None:
        self.is_shut_down = True


@dataclass
class FakeMatlab:
    fails_on_finishing: bool = False
    started: list[FakeMatlabEngine] = field(default_factory=list)

    def start_matlab(self) -> FakeMatlabEngine:
        engine = FakeMatlabEngine(fails_on_finishing=self.fails_on_finishing)
        self.started.append(engine)
        return engine
