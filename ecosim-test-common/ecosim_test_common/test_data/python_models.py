import functools
from dataclasses import dataclass
from typing import Any, Callable


def _forwarding_decorator(do_step: Callable[..., dict[str, float]]) -> Callable[..., dict[str, float]]:
    """A decorator as a model may use for logging or timing, made with functools.wraps."""

    @functools.wraps(do_step)
    def forward(*arguments: Any, **keyword_arguments: Any) -> dict[str, float]:
        return do_step(*arguments, **keyword_arguments)

    return forward


@dataclass
class DoublingModel:
    """y = 2 * u, the model of the client tests of the Python client."""

    holds_state: bool = False

    def initialize(self) -> dict[str, float]:
        self.holds_state = True
        return {"y": 0.0}

    def do_step(self, value_dict: dict[str, float]) -> dict[str, float]:
        return {"y": 2 * value_dict["u"]}

    def clear(self) -> None:
        self.holds_state = False


@dataclass
class ClockModel:
    """Returns the simulation time and the step size it gets in do_step()."""

    def initialize(self) -> dict[str, float]:
        return {"time": 0.0, "step_size": 0.0}

    def do_step(self, value_dict: dict[str, float], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        return {"time": current_simulation_time, "step_size": step_size_in_seconds}

    def clear(self) -> None:
        pass


@dataclass
class KeywordOnlyClockModel:
    """Takes the simulation time as a keyword-only parameter of do_step()."""

    def initialize(self) -> dict[str, float]:
        return {"time": 0.0}

    def do_step(self, value_dict: dict[str, float], *, current_simulation_time: float) -> dict[str, float]:
        return {"time": current_simulation_time}

    def clear(self) -> None:
        pass


@dataclass
class PositionalOnlyClockModel:
    """Has current_simulation_time as a positional-only parameter, which cannot be passed by name."""

    def initialize(self) -> dict[str, float]:
        return {"time": 0.0}

    def do_step(self, value_dict: dict[str, float], current_simulation_time: float = -1.0, /) -> dict[str, float]:
        return {"time": current_simulation_time}

    def clear(self) -> None:
        pass


@dataclass
class DecoratedClockModel:
    """Has its do_step() behind a decorator."""

    def initialize(self) -> dict[str, float]:
        return {"time": 0.0}

    @_forwarding_decorator
    def do_step(self, value_dict: dict[str, float], current_simulation_time: float) -> dict[str, float]:
        return {"time": current_simulation_time}

    def clear(self) -> None:
        pass


@dataclass
class EchoModel:
    """Gives the input u back as the output y, and pops it from value_dict as a model may."""

    def initialize(self) -> dict[str, Any]:
        return {"y": 0.0}

    def do_step(self, value_dict: dict[str, Any]) -> dict[str, Any]:
        return {"y": value_dict.pop("u")}

    def clear(self) -> None:
        pass


@dataclass
class DividingByZeroModel:
    """Divides by zero in initialize(), a mistake in the code of a model."""

    def initialize(self) -> dict[str, float]:
        return {"share": 1 / 0}

    def do_step(self, value_dict: dict[str, float]) -> dict[str, float]:
        return {"share": 0.0}

    def clear(self) -> None:
        pass


@dataclass
class ScriptedOutputsModel:
    """Returns what a test gives it, also what a model must not return."""

    start_outputs: Any = None
    step_outputs: Any = None
    clear_calls: int = 0

    def initialize(self) -> Any:
        return self.start_outputs

    def do_step(self, value_dict: dict[str, float]) -> Any:
        return self.step_outputs

    def clear(self) -> None:
        self.clear_calls += 1


@dataclass(frozen=True)
class NumpyLikeNumber:
    """A number that JSON cannot store, like numpy.float32, until float() turns it into one."""

    value: float

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True)
class NumpyLikeArray:
    """An array of one value, which float() turns into a number, as numpy does."""

    value: float
    ndim: int = 1

    def __float__(self) -> float:
        return self.value
