from __future__ import annotations

import math
from dataclasses import dataclass

from ecosim_common.config.interface_type import InterfaceType

from ecosim.new.interface_address import InterfaceAddress
from ecosim.new.simulation_model import SimulationModel, input_at
from ecosim.new.wiring import Wiring, ensure_it_exists

StartValue = float | list[float]


@dataclass(frozen=True)
class DelayedInput:
    """A connected input that gets the value of the step before, and its start value in the first step."""

    input: InterfaceAddress
    start_value: StartValue

    @staticmethod
    def of_texts(texts: list[str], models: list[SimulationModel], wiring: Wiring) -> list[DelayedInput]:
        """From the values of --logical-delay, like heating.T_room or heating.T_room=293.15."""
        delayed: list[DelayedInput] = []
        for text in texts:
            delayed_input = DelayedInput._of_text(text=text, models=models, wiring=wiring)
            if delayed_input.input in [earlier.input for earlier in delayed]:
                raise ValueError(f"--logical-delay {text}: {delayed_input.input} has a logical delay already.")
            delayed.append(delayed_input)
        _ensure_own_outputs_are_delayed(wiring=wiring, delayed=delayed)
        return delayed

    @staticmethod
    def _of_text(text: str, models: list[SimulationModel], wiring: Wiring) -> DelayedInput:
        option_text = f"--logical-delay {text}"
        address_text, separator, start_text = text.partition("=")
        address = InterfaceAddress.of_text(text=address_text, option_text=option_text)
        other_kind_hint = "A logical delay goes on an input, like heating.T_room"
        ensure_it_exists(models=models, address=address, interface_type=InterfaceType.INPUT, option_text=option_text, other_kind_hint=other_kind_hint)
        if wiring.connection_of(address=address) is None:
            raise ValueError(f"{option_text}: {address} is not connected, so there is nothing to delay.")
        interface = input_at(models=models, address=address)
        # FMI 2.0 and FMI 3.0 require a start value for an input, but an FMU may still lack one
        start = start_text if separator else interface.start
        if start is None:
            raise ValueError(f"{option_text}: its FMU has no start value. Give one, like --logical-delay {address}=0")
        return DelayedInput(input=address, start_value=_start_value(text=start, shape=interface.shape, option_text=option_text))


def _start_value(text: str, shape: tuple[int, ...], option_text: str) -> StartValue:
    # an FMU writes the start of an FMI 3.0 array with spaces, like '1 2 3', and the command line with commas
    try:
        values = [float(value) for value in text.replace(",", " ").split()]
    except ValueError:
        values = []
    # nan and inf would make simulation.json no standard JSON
    if len(values) != math.prod(shape) or not all(math.isfinite(value) for value in values):
        expected = f"{math.prod(shape)} numbers separated by commas" if shape else "a number"
        raise ValueError(f"{option_text}: the start value must be {expected}, not '{text}'.")
    return values if shape else values[0]


def _ensure_own_outputs_are_delayed(wiring: Wiring, delayed: list[DelayedInput]) -> None:
    # the server hands a model its own output only through a logical delay
    delayed_inputs = [delayed_input.input for delayed_input in delayed]
    for connection in wiring.connections:
        if connection.input.model == connection.output.model and connection.input not in delayed_inputs:
            raise ValueError(
                f"--connect {connection.input}={connection.output} feeds {connection.input.model} its own output, "
                + f"which needs --logical-delay {connection.input}",
            )
