from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest
from ecosim_client_matlab import matlab_client


@dataclass
class FakeMatlabEngine:
    """
    Stands in for 'matlab.engine.MatlabEngine', which needs a Matlab installation.

    'step' doubles the input 'u' into the output 'y' and reports the 'client_time' it was called with as 'time',
    so a test can see which simulation time the client hands to its model.
    """

    workspace: dict[str, Any] = field(default_factory=dict)
    paths: list[str] = field(default_factory=list)
    is_shut_down: bool = False

    def addpath(self, path: str) -> None:
        self.paths.append(path)

    def setup(self, nargout: int = 0) -> None:
        self.workspace.update(y=0.0, time=0.0)

    def step(self, nargout: int = 0, stdout: Any = None) -> None:
        self.workspace.update(y=2 * self.workspace["u"], time=self.workspace["client_time"])

    def finishing(self, nargout: int = 0, stdout: Any = None) -> None:
        pass

    def shutdown(self, nargout: int = 0) -> None:
        self.is_shut_down = True


@dataclass
class FakeMatlab:
    started: list[FakeMatlabEngine] = field(default_factory=list)

    def start_matlab(self) -> FakeMatlabEngine:
        engine = FakeMatlabEngine()
        self.started.append(engine)
        return engine


@pytest.fixture
def fake_matlab(monkeypatch: pytest.MonkeyPatch) -> FakeMatlab:
    """Lets 'MatlabClient' start its engines from a new fake, for the current test only."""
    fake = FakeMatlab()
    # without a Matlab installation the module never bound 'matlab', hence 'raising=False'
    monkeypatch.setattr(matlab_client, "matlab", SimpleNamespace(engine=fake), raising=False)
    return fake
