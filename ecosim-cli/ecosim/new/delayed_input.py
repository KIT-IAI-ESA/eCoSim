from __future__ import annotations

import math
from dataclasses import dataclass

from ecosim_common.config.interface_type import InterfaceType

from ecosim.new.input_connections import InputConnections, ensure_it_exists
from ecosim.new.simulation_model import SimulationModel, input_at
from ecosim.new.simulation_model_interface_id import SimulationModelInterfaceId

LogicalDelayStartValue = float | list[float]


@dataclass(frozen=True)
class DelayedInput:
    input: SimulationModelInterfaceId
    start_value: LogicalDelayStartValue

    @staticmethod
    def of_texts(texts: list[str], models: list[SimulationModel], input_connections: InputConnections) -> list[DelayedInput]:
        delayed: list[DelayedInput] = []
        for text in texts:
            delayed_input = DelayedInput._of_text(text=text, models=models, input_connections=input_connections)
            if delayed_input.input in [earlier.input for earlier in delayed]:
                raise ValueError(f"--logical-delay {text}: {delayed_input.input} has a logical delay already.")
            delayed.append(delayed_input)
        _ensure_own_outputs_are_delayed(input_connections=input_connections, delayed=delayed)
        return delayed

    @staticmethod
    def _of_text(text: str, models: list[SimulationModel], input_connections: InputConnections) -> DelayedInput:
        option_text = f"--logical-delay {text}"
        interface_id_text, separator, start_text = text.partition("=")
        interface_id = SimulationModelInterfaceId.of_text(text=interface_id_text, option_text=option_text)
        other_kind_hint = "A logical delay goes on an input, like heating.T_room"
        ensure_it_exists(
            models=models,
            interface_id=interface_id,
            interface_type=InterfaceType.INPUT,
            option_text=option_text,
            other_kind_hint=other_kind_hint,
        )
        if input_connections.connection_of(interface_id=interface_id) is None:
            raise ValueError(f"{option_text}: {interface_id} is not connected.")
        interface = input_at(models=models, interface_id=interface_id)
        # FMI requires a start value for an input, some FMUs still have none
        start = start_text if separator else interface.start
        if start is None:
            raise ValueError(f"{option_text}: its FMU has no start value. Pass one, like --logical-delay {interface_id}=0")
        return DelayedInput(input=interface_id, start_value=_start_value(text=start, shape=interface.shape, option_text=option_text))


def _start_value(text: str, shape: tuple[int, ...], option_text: str) -> LogicalDelayStartValue:
    # an FMU separates the start values of an array with spaces
    try:
        values = [float(value) for value in text.replace(",", " ").split()]
    except ValueError:
        values = []
    # nan and inf are not standard JSON
    if len(values) != math.prod(shape) or not all(math.isfinite(value) for value in values):
        expected = f"{math.prod(shape)} numbers separated by commas" if shape else "a number"
        raise ValueError(f"{option_text}: the start value must be {expected}, not '{text}'.")
    return values if shape else values[0]


def _ensure_own_outputs_are_delayed(input_connections: InputConnections, delayed: list[DelayedInput]) -> None:
    # the server hands a model its own output only through a logical delay
    delayed_inputs = [delayed_input.input for delayed_input in delayed]
    for connection in input_connections.connections:
        if connection.input.model == connection.output.model and connection.input not in delayed_inputs:
            raise ValueError(
                f"--connect {connection.input}={connection.output} connects {connection.input.model} to its own output. "
                + f"This needs --logical-delay {connection.input}",
            )
