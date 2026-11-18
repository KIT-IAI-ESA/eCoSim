from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from ecosim_common.communication.data.protocol_interface_value import InterfaceValue


@runtime_checkable
class PythonModel(Protocol):
    def initialize(self) -> Mapping[str, InterfaceValue]: ...

    # positional, so a model can name the parameters as it likes
    def do_step(
        self,
        inputs: dict[str, Any],
        current_simulation_time: float,
        step_size_in_seconds: float,
        /,
    ) -> Mapping[str, InterfaceValue]: ...

    def clear(self) -> None: ...
