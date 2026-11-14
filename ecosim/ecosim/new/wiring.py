from __future__ import annotations

import math
from dataclasses import dataclass

from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.readable_count import readable_count
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface

from ecosim.new.interface_address import InterfaceAddress
from ecosim.new.simulation_model import SimulationModel, input_at, model_named, output_at
from ecosim.report_lines import and_joined


@dataclass(frozen=True)
class Connection:
    input: InterfaceAddress
    output: InterfaceAddress
    # False for a connection given with --connect
    matched_by_name: bool


@dataclass(frozen=True)
class OpenInput:
    input: InterfaceAddress
    # the outputs of other models with its name: none, several, or ones that hold another number of values
    outputs_with_its_name: tuple[InterfaceAddress, ...]


@dataclass(frozen=True)
class Wiring:
    """Each input connected as --connect says, else to the one output of another model with its name, where '.' and '_' count as the same."""

    connections: tuple[Connection, ...]
    open_inputs: tuple[OpenInput, ...]

    @staticmethod
    def of_models(models: list[SimulationModel], given_connections: list[str]) -> Wiring:
        given = _given_connections(models=models, texts=given_connections)
        outputs = [address for model in models for address in model.output_addresses()]
        connections: list[Connection] = []
        open_inputs: list[OpenInput] = []
        for address in (address for model in models for address in model.input_addresses()):
            with_its_name = tuple(output for output in outputs if output.model != address.model and same_name(first=output.name, second=address.name))
            of_its_size = [output for output in with_its_name if sizes_fit(models=models, input_address=address, output_address=output)]
            if address in given:
                connections.append(Connection(input=address, output=given[address], matched_by_name=False))
            elif len(of_its_size) == 1:
                connections.append(Connection(input=address, output=of_its_size[0], matched_by_name=True))
            else:
                open_inputs.append(OpenInput(input=address, outputs_with_its_name=with_its_name))
        return Wiring(connections=tuple(connections), open_inputs=tuple(open_inputs))

    def connection_of(self, address: InterfaceAddress) -> Connection | None:
        return next((connection for connection in self.connections if connection.input == address), None)


def same_name(first: str, second: str) -> bool:
    # Modelica exports buses with dots, like weatherBus.TDryBul, and the inputs fed by them often with underscores
    return first.replace(".", "_") == second.replace(".", "_")


def ensure_it_exists(
    models: list[SimulationModel],
    address: InterfaceAddress,
    interface_type: InterfaceType,
    option_text: str,
    other_kind_hint: str,
) -> None:
    """Raises ValueError, with a close name if there is one, for an input or an output that no model has."""
    model_names = [model.name for model in models]
    if address.model not in model_names:
        hint = did_you_mean(name=address.model, known_names=model_names) or f" The models are {and_joined(texts=model_names)}."
        raise ValueError(f"{option_text}: there is no model {address.model}.{hint}")
    model = model_named(models=models, name=address.model)
    inputs, outputs = [interface.name for interface in model.interfaces.inputs], [interface.name for interface in model.interfaces.outputs]
    names, other_names = (inputs, outputs) if interface_type is InterfaceType.INPUT else (outputs, inputs)
    if address.name in names:
        return
    if address.name in other_names:
        raise ValueError(f"{option_text}: {address} is not an {interface_type.value}. {other_kind_hint}")
    raise ValueError(f"{option_text}: {model.name} has no {interface_type.value} {address.name}.{did_you_mean(name=address.name, known_names=names)}")


def _given_connections(models: list[SimulationModel], texts: list[str]) -> dict[InterfaceAddress, InterfaceAddress]:
    given: dict[InterfaceAddress, InterfaceAddress] = {}
    order_hint = "Write the input first, then '=' and the output."
    for text in texts:
        option_text = f"--connect {text}"
        input_text, separator, output_text = text.partition("=")
        if not separator:
            raise ValueError(f"{option_text}: write the input, '=' and the output, like house.T_out=weather.T_dry")
        input_address = InterfaceAddress.of_text(text=input_text, option_text=option_text)
        output_address = InterfaceAddress.of_text(text=output_text, option_text=option_text)
        for address, interface_type in ((input_address, InterfaceType.INPUT), (output_address, InterfaceType.OUTPUT)):
            ensure_it_exists(models=models, address=address, interface_type=interface_type, option_text=option_text, other_kind_hint=order_hint)
        if input_address in given:
            raise ValueError(f"{option_text}: {input_address} is connected to {given[input_address]} already. An input takes one output.")
        _ensure_sizes_fit(models=models, input_address=input_address, output_address=output_address, option_text=option_text)
        given[input_address] = output_address
    return given


def _ensure_sizes_fit(models: list[SimulationModel], input_address: InterfaceAddress, output_address: InterfaceAddress, option_text: str) -> None:
    # the FMI 3.0 client would stop at the first step
    if not sizes_fit(models=models, input_address=input_address, output_address=output_address):
        output_values = readable_count(count=value_count(interface=output_at(models=models, address=output_address)), noun="value")
        input_size = value_count(interface=input_at(models=models, address=input_address))
        raise ValueError(f"{option_text}: {output_address} holds {output_values}, but {input_address} takes {input_size}.")


def sizes_fit(models: list[SimulationModel], input_address: InterfaceAddress, output_address: InterfaceAddress) -> bool:
    # the FMI 3.0 client checks only that an input gets as many values as it takes
    input_size = value_count(interface=input_at(models=models, address=input_address))
    return input_size == value_count(interface=output_at(models=models, address=output_address))


def value_count(interface: FMUInterface) -> int:
    """1 for a scalar, else the number of values of an FMI 3.0 array."""
    return math.prod(interface.shape)
