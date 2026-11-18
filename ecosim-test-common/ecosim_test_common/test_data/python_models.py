from dataclasses import dataclass
from typing import Any


@dataclass
class DoublingModel:
    holds_state: bool = False

    def initialize(self) -> dict[str, float]:
        self.holds_state = True
        return {"y": 0.0}

    def do_step(self, inputs: dict[str, Any], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        return {"y": 2 * inputs["u"]}

    def clear(self) -> None:
        self.holds_state = False


@dataclass
class ClockModel:
    def initialize(self) -> dict[str, float]:
        return {"time": 0.0, "step_size": 0.0}

    def do_step(self, inputs: dict[str, Any], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        return {"time": current_simulation_time, "step_size": step_size_in_seconds}

    def clear(self) -> None:
        pass


@dataclass
class EchoModel:
    """Returns the input u as the output y and removes it from the inputs."""

    def initialize(self) -> dict[str, Any]:
        return {"y": 0.0}

    def do_step(self, inputs: dict[str, Any], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, Any]:
        return {"y": inputs.pop("u")}

    def clear(self) -> None:
        pass


@dataclass
class ScriptedOutputsModel:
    start_outputs: Any = None
    step_outputs: Any = None
    clear_calls: int = 0

    def initialize(self) -> Any:
        return self.start_outputs

    def do_step(self, inputs: dict[str, Any], current_simulation_time: float, step_size_in_seconds: float) -> Any:
        return self.step_outputs

    def clear(self) -> None:
        self.clear_calls += 1
