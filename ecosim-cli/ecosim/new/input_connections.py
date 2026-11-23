from __future__ import annotations

import math
from dataclasses import dataclass

from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.readable_count import readable_count
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface

from ecosim.new.simulation_model import SimulationModel, input_at, model_named, output_at
from ecosim.new.simulation_model_interface_id import SimulationModelInterfaceId
from ecosim.report_lines import and_joined


@dataclass(frozen=True)
class Connection:
    input: SimulationModelInterfaceId
    output: SimulationModelInterfaceId
    matched_by_name: bool


@dataclass(frozen=True)
class UnconnectedInput:
    input: SimulationModelInterfaceId
    outputs_with_its_name: tuple[SimulationModelInterfaceId, ...]


@dataclass(frozen=True)
class InputConnections:
    """Connects each input to the one output of another model with its name, unless --connect says otherwise."""

    connections: tuple[Connection, ...]
    unconnected_inputs: tuple[UnconnectedInput, ...]

    @staticmethod
    def of_models(models: list[SimulationModel], given_connections: list[str]) -> InputConnections:
        given = _given_connections(models=models, texts=given_connections)
        outputs = [interface_id for model in models for interface_id in model.output_ids()]
        connections: list[Connection] = []
        unconnected_inputs: list[UnconnectedInput] = []
        for interface_id in (interface_id for model in models for interface_id in model.input_ids()):
            with_its_name = tuple(
                output for output in outputs if output.model != interface_id.model and same_name(first=output.name, second=interface_id.name)
            )
            of_its_size = [output for output in with_its_name if sizes_fit(models=models, input_id=interface_id, output_id=output)]
            if interface_id in given:
                connections.append(Connection(input=interface_id, output=given[interface_id], matched_by_name=False))
            elif len(of_its_size) == 1:
                connections.append(Connection(input=interface_id, output=of_its_size[0], matched_by_name=True))
            else:
                unconnected_inputs.append(UnconnectedInput(input=interface_id, outputs_with_its_name=with_its_name))
        return InputConnections(connections=tuple(connections), unconnected_inputs=tuple(unconnected_inputs))

    def connection_of(self, interface_id: SimulationModelInterfaceId) -> Connection | None:
        return next((connection for connection in self.connections if connection.input == interface_id), None)


def same_name(first: str, second: str) -> bool:
    # Modelica exports weatherBus.TDryBul, the input for it is often weatherBus_TDryBul
    return first.replace(".", "_") == second.replace(".", "_")


def ensure_it_exists(
    models: list[SimulationModel],
    interface_id: SimulationModelInterfaceId,
    interface_type: InterfaceType,
    option_text: str,
    other_kind_hint: str,
) -> None:
    model_names = [model.name for model in models]
    if interface_id.model not in model_names:
        hint = did_you_mean(name=interface_id.model, known_names=model_names) or f" The models are {and_joined(texts=model_names)}."
        raise ValueError(f"{option_text}: there is no model {interface_id.model}.{hint}")
    model = model_named(models=models, name=interface_id.model)
    inputs, outputs = [interface.name for interface in model.interfaces.inputs], [interface.name for interface in model.interfaces.outputs]
    names, other_names = (inputs, outputs) if interface_type is InterfaceType.INPUT else (outputs, inputs)
    if interface_id.name in names:
        return
    if interface_id.name in other_names:
        raise ValueError(f"{option_text}: {interface_id} is not an {interface_type.value}. {other_kind_hint}")
    raise ValueError(
        f"{option_text}: {model.name} has no {interface_type.value} {interface_id.name}.{did_you_mean(name=interface_id.name, known_names=names)}",
    )


def _given_connections(models: list[SimulationModel], texts: list[str]) -> dict[SimulationModelInterfaceId, SimulationModelInterfaceId]:
    given: dict[SimulationModelInterfaceId, SimulationModelInterfaceId] = {}
    order_hint = "Write the input first, then '=' and the output."
    for text in texts:
        option_text = f"--connect {text}"
        input_text, separator, output_text = text.partition("=")
        if not separator:
            raise ValueError(f"{option_text}: write the input, '=' and the output, like house.T_out=weather.T_dry")
        input_id = SimulationModelInterfaceId.of_text(text=input_text, option_text=option_text)
        output_id = SimulationModelInterfaceId.of_text(text=output_text, option_text=option_text)
        for interface_id, interface_type in ((input_id, InterfaceType.INPUT), (output_id, InterfaceType.OUTPUT)):
            ensure_it_exists(
                models=models,
                interface_id=interface_id,
                interface_type=interface_type,
                option_text=option_text,
                other_kind_hint=order_hint,
            )
        if input_id in given:
            raise ValueError(f"{option_text}: {input_id} is connected to {given[input_id]} already.")
        _ensure_sizes_fit(models=models, input_id=input_id, output_id=output_id, option_text=option_text)
        given[input_id] = output_id
    return given


def _ensure_sizes_fit(
    models: list[SimulationModel],
    input_id: SimulationModelInterfaceId,
    output_id: SimulationModelInterfaceId,
    option_text: str,
) -> None:
    if not sizes_fit(models=models, input_id=input_id, output_id=output_id):
        output_values = readable_count(count=value_count(interface=output_at(models=models, interface_id=output_id)), noun="value")
        input_size = value_count(interface=input_at(models=models, interface_id=input_id))
        raise ValueError(f"{option_text}: {output_id} has {output_values}, but {input_id} takes {input_size}.")


def sizes_fit(models: list[SimulationModel], input_id: SimulationModelInterfaceId, output_id: SimulationModelInterfaceId) -> bool:
    # the FMI 3.0 client checks only the number of values
    input_size = value_count(interface=input_at(models=models, interface_id=input_id))
    return input_size == value_count(interface=output_at(models=models, interface_id=output_id))


def value_count(interface: FMUInterface) -> int:
    return math.prod(interface.shape)
