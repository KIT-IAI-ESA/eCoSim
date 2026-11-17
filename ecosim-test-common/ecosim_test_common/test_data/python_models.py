import functools
from dataclasses import dataclass
from typing import Any, Callable


def _forwarding_decorator(do_step: Callable[..., dict[str, float]]) -> Callable[..., dict[str, float]]:
    @functools.wraps(do_step)
    def forward(*arguments: Any, **keyword_arguments: Any) -> dict[str, float]:
        return do_step(*arguments, **keyword_arguments)

    return forward


@dataclass
class DoublingModel:
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
    def initialize(self) -> dict[str, float]:
        return {"time": 0.0, "step_size": 0.0}

    def do_step(self, value_dict: dict[str, float], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        return {"time": current_simulation_time, "step_size": step_size_in_seconds}

    def clear(self) -> None:
        pass


@dataclass
class KeywordOnlyClockModel:
    def initialize(self) -> dict[str, float]:
        return {"time": 0.0}

    def do_step(self, value_dict: dict[str, float], *, current_simulation_time: float) -> dict[str, float]:
        return {"time": current_simulation_time}

    def clear(self) -> None:
        pass


@dataclass
class PositionalOnlyClockModel:
    def initialize(self) -> dict[str, float]:
        return {"time": 0.0}

    def do_step(self, value_dict: dict[str, float], current_simulation_time: float = -1.0, /) -> dict[str, float]:
        return {"time": current_simulation_time}

    def clear(self) -> None:
        pass


@dataclass
class DecoratedClockModel:
    def initialize(self) -> dict[str, float]:
        return {"time": 0.0}

    @_forwarding_decorator
    def do_step(self, value_dict: dict[str, float], current_simulation_time: float) -> dict[str, float]:
        return {"time": current_simulation_time}

    def clear(self) -> None:
        pass


@dataclass
class EchoModel:
    """Returns the input u as the output y and removes it from value_dict."""

    def initialize(self) -> dict[str, Any]:
        return {"y": 0.0}

    def do_step(self, value_dict: dict[str, Any]) -> dict[str, Any]:
        return {"y": value_dict.pop("u")}

    def clear(self) -> None:
        pass


@dataclass
class DividingByZeroModel:
    def initialize(self) -> dict[str, float]:
        return {"share": 1 / 0}

    def do_step(self, value_dict: dict[str, float]) -> dict[str, float]:
        return {"share": 0.0}

    def clear(self) -> None:
        pass


@dataclass
class ScriptedOutputsModel:
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
    value: float

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True)
class NumpyLikeArray:
    """Acts like a numpy array with one value, float() takes it."""

    value: float
    ndim: int = 1

    def __float__(self) -> float:
        return self.value
