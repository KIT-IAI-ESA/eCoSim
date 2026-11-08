import io
from typing import Any, Protocol


class MatlabScript(Protocol):
    def __call__(self, *, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None: ...


class MatlabWorkspace(Protocol):
    def __getitem__(self, name: str) -> Any: ...

    def __setitem__(self, name: str, value: Any) -> None: ...


class MatlabEngine(Protocol):
    """The part of 'matlab.engine.MatlabEngine' the client uses, which comes without type hints."""

    @property
    def workspace(self) -> MatlabWorkspace: ...

    def addpath(self, path: str) -> object: ...

    def setup(self, *, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None: ...

    def step(self, *, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None: ...

    def finishing(self, *, nargout: int, stdout: io.StringIO, stderr: io.StringIO) -> None: ...

    def quit(self) -> None: ...


def start_matlab() -> MatlabEngine:
    try:
        import matlab.engine
    except (ImportError, RuntimeError) as error:
        raise ImportError(
            "The MATLAB engine for Python is missing or does not match the MATLAB installation. Install the extra of your MATLAB version, "
            "for example with 'uv sync --extra R2024b' in ecosim-client-matlab.",
        ) from error
    return matlab.engine.start_matlab()
