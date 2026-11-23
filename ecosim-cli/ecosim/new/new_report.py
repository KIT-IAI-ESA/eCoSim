from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.tech.close_name import closest_name
from ecosim_common.tech.readable_count import readable_count
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig

from ecosim.check.check_report import findings_lines, fix_line
from ecosim.check.simulation_check import SimulationCheck
from ecosim.new.delayed_input import DelayedInput, LogicalDelayStartValue
from ecosim.new.input_connections import Connection, InputConnections, UnconnectedInput, sizes_fit, value_count
from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel, input_at, output_at
from ecosim.new.simulation_model_interface_id import SimulationModelInterfaceId
from ecosim.report_lines import and_joined, client_type_text, command_text, ecosim_program, length_line, simulator_lines, with_shown_paths
from ecosim.simulation_directory import SimulationDirectory


@dataclass(frozen=True)
class NewReport:
    simulation: SimulationDirectory
    models: list[SimulationModel]
    input_connections: InputConnections
    delayed: list[DelayedInput]
    length: SimulationLength
    check: SimulationCheck

    def lines(self) -> list[str]:
        lines = [self._summary_line()]
        if self.check.simulation_config is not None:
            lines.append(length_line(simulation_config=self.check.simulation_config))
        lines += [line for line in [self.length.defaults_line()] if line is not None]
        lines += simulator_lines(simulators=self.check.simulators)
        lines += self._connection_lines()
        lines += self._unconnected_input_lines()
        lines += self._left_out_lines()
        lines += findings_lines(findings=self.check.findings)
        lines += self._next_command_lines()
        return [with_shown_paths(text=line) for line in lines]

    def _summary_line(self) -> str:
        counts = [
            readable_count(count=len(self.models), noun="simulator"),
            readable_count(count=len(self.input_connections.connections), noun="connection"),
        ]
        problems, warnings = self.check.findings.problems, self.check.findings.warnings
        counts.append(readable_count(count=len(problems), noun="problem") if problems else "no problems")
        if warnings:
            counts.append(readable_count(count=len(warnings), noun="warning"))
        return f"Wrote {self.simulation.name}: {', '.join(counts)}."

    def _connection_lines(self) -> list[str]:
        if not self.input_connections.connections:
            return []
        groups: dict[tuple[str, str], list[Connection]] = {}
        for connection in self.input_connections.connections:
            groups.setdefault((connection.input.model, connection.output.model), []).append(connection)
        lines = ["Connections:"]
        for (input_model, output_model), group in groups.items():
            width = max(len(connection.input.name) for connection in group)
            lines.append(f"  {input_model} <- {output_model}, {readable_count(count=len(group), noun='connection')}")
            lines += [self._connection_line(connection=connection, width=width) for connection in group]
        return lines

    def _connection_line(self, connection: Connection, width: int) -> str:
        notes = [] if connection.matched_by_name else ["given with --connect"]
        delayed_input = next((delayed_input for delayed_input in self.delayed if delayed_input.input == connection.input), None)
        if delayed_input is not None:
            notes.append(f"one step later, starts at {_start_value_text(start_value=delayed_input.start_value)}")
        input_unit = input_at(models=self.models, interface_id=connection.input).unit
        output_unit = output_at(models=self.models, interface_id=connection.output).unit
        # units are not converted
        if input_unit and output_unit and input_unit != output_unit:
            notes.append(f"the output is in {output_unit}, the input in {input_unit}")
        line = f"    {connection.input.name:<{width}}  <-  {connection.output.name}"
        return f"{line}   ({', '.join(notes)})" if notes else line

    def _unconnected_input_lines(self) -> list[str]:
        if not self.input_connections.unconnected_inputs:
            return []
        reasons = [
            f"  {unconnected_input.input}: {self._reason_it_is_unconnected(unconnected_input=unconnected_input)}"
            for unconnected_input in self.input_connections.unconnected_inputs
        ]
        return ["Not connected. These inputs keep the start value of their FMU:", *reasons]

    def _reason_it_is_unconnected(self, unconnected_input: UnconnectedInput) -> str:
        outputs = unconnected_input.outputs_with_its_name
        of_its_size = [output for output in outputs if sizes_fit(models=self.models, input_id=unconnected_input.input, output_id=output)]
        if len(of_its_size) > 1:
            outputs_text = and_joined(texts=[str(output) for output in of_its_size])
            return f"{len(of_its_size)} outputs have this name: {outputs_text}. Choose one with --connect {unconnected_input.input}={of_its_size[0]}"
        if outputs:
            input_size = value_count(interface=input_at(models=self.models, interface_id=unconnected_input.input))
            output_values = readable_count(count=value_count(interface=output_at(models=self.models, interface_id=outputs[0])), noun="value")
            return f"the output {outputs[0]} has this name, but it has {output_values} and the input takes {input_size}."
        return f"no output of another model has this name.{self._hint_for(interface_id=unconnected_input.input)}"

    def _hint_for(self, interface_id: SimulationModelInterfaceId) -> str:
        outputs = [output for model in self.models if model.name != interface_id.model for output in model.output_ids()]
        # a lower cutoff would suggest Float64_discrete_output for Float64_discrete_input
        closest = closest_name(name=interface_id.name, known_names=[output.name for output in outputs], cutoff=0.9)
        if closest is None:
            return ""
        output = next(output for output in outputs if output.name == closest)
        return f" Did you mean {output}? Then add --connect {interface_id}={output}"

    def _left_out_lines(self) -> list[str]:
        lines = [_left_out_line(model=model) for model in self.models if model.interfaces.skipped]
        return ["Left out of the .fmc files:", *lines] if lines else []

    def _next_command_lines(self) -> list[str]:
        check_command = command_text(arguments=[*ecosim_program(), "check", str(self.simulation.path)])
        problems = self.check.findings.problems
        if problems:
            return [fix_line(problems=problems, check_command=check_command)]
        run_command = command_text(arguments=[*ecosim_program(), "run", str(self.simulation.path)])
        return [f"After a change, check it with: {check_command}", f"Run it with: {run_command}"]


def _left_out_line(model: SimulationModel) -> str:
    variables = ", ".join(f"{variable.name} ({variable.type})" for variable in model.interfaces.skipped)
    client = client_type_text(client_type=model.interfaces.client_type())
    supported_type = FMUBaseConfig.supported_type(fmi_major_version=int(model.interfaces.fmi_version.split(".")[0]))
    return f"  {model.name}: {variables}. The {client} client exchanges {supported_type} variables only."


def _start_value_text(start_value: LogicalDelayStartValue) -> str:
    values = start_value if isinstance(start_value, list) else [start_value]
    return ", ".join(str(int(value)) if value.is_integer() else str(value) for value in values)
