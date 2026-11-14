from __future__ import annotations

import math
from dataclasses import dataclass

from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface

from ecosim.new.interface_address import InterfaceAddress
from ecosim.new.simulation_model import SimulationModel, input_at, output_at


@dataclass(frozen=True)
class Connection:
    input: InterfaceAddress
    output: InterfaceAddress


@dataclass(frozen=True)
class OpenInput:
    input: InterfaceAddress
    # the outputs of other models with its name: none, several, or ones that hold another number of values
    outputs_with_its_name: tuple[InterfaceAddress, ...]


@dataclass(frozen=True)
class Wiring:
    """Each input connected to the one output of another model with its name, where '.' and '_' count as the same."""

    connections: tuple[Connection, ...]
    open_inputs: tuple[OpenInput, ...]

    @staticmethod
    def of_models(models: list[SimulationModel]) -> Wiring:
        outputs = [address for model in models for address in model.output_addresses()]
        connections: list[Connection] = []
        open_inputs: list[OpenInput] = []
        for address in (address for model in models for address in model.input_addresses()):
            with_its_name = tuple(output for output in outputs if output.model != address.model and same_name(first=output.name, second=address.name))
            of_its_size = [output for output in with_its_name if sizes_fit(models=models, input_address=address, output_address=output)]
            if len(of_its_size) == 1:
                connections.append(Connection(input=address, output=of_its_size[0]))
            else:
                open_inputs.append(OpenInput(input=address, outputs_with_its_name=with_its_name))
        return Wiring(connections=tuple(connections), open_inputs=tuple(open_inputs))

    def connection_of(self, address: InterfaceAddress) -> Connection | None:
        return next((connection for connection in self.connections if connection.input == address), None)


def same_name(first: str, second: str) -> bool:
    # Modelica exports buses with dots, like weatherBus.TDryBul, and the inputs fed by them often with underscores
    return first.replace(".", "_") == second.replace(".", "_")


def sizes_fit(models: list[SimulationModel], input_address: InterfaceAddress, output_address: InterfaceAddress) -> bool:
    # the FMI 3.0 client checks only that an input gets as many values as it takes
    input_size = value_count(interface=input_at(models=models, address=input_address))
    return input_size == value_count(interface=output_at(models=models, address=output_address))


def value_count(interface: FMUInterface) -> int:
    """1 for a scalar, else the number of values of an FMI 3.0 array."""
    return math.prod(interface.shape)
