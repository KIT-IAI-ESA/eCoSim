from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.tech.close_name import closest_name
from ecosim_common.tech.readable_count import readable_count
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig

from ecosim.check.check_report import findings_lines, fix_line
from ecosim.check.simulation_check import SimulationCheck
from ecosim.new.interface_address import InterfaceAddress
from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel, input_at, output_at
from ecosim.new.wiring import Connection, OpenInput, Wiring, sizes_fit, value_count
from ecosim.report_lines import and_joined, client_type_text, command_text, ecosim_program, length_line, simulator_lines, with_shown_paths
from ecosim.simulation_folder import SimulationFolder


@dataclass(frozen=True)
class NewReport:
    """What ecosim new wrote, in the form of ecosim check, and the commands to go on with."""

    simulation: SimulationFolder
    models: list[SimulationModel]
    wiring: Wiring
    length: SimulationLength
    check: SimulationCheck

    def lines(self) -> list[str]:
        lines = [self._summary_line()]
        if self.check.simulation_config is not None:
            lines.append(length_line(simulation_config=self.check.simulation_config))
        lines += [line for line in [self.length.defaults_line()] if line is not None]
        lines += simulator_lines(simulators=self.check.simulators)
        lines += self._connection_lines()
        lines += self._open_input_lines()
        lines += self._left_out_lines()
        lines += findings_lines(findings=self.check.findings)
        lines += self._next_command_lines()
        return [with_shown_paths(text=line) for line in lines]

    def _summary_line(self) -> str:
        """Like 'Wrote my_simulation: 3 simulators, 18 connections, no problems.'"""
        counts = [readable_count(count=len(self.models), noun="simulator"), readable_count(count=len(self.wiring.connections), noun="connection")]
        problems, warnings = self.check.findings.problems, self.check.findings.warnings
        counts.append(readable_count(count=len(problems), noun="problem") if problems else "no problems")
        if warnings:
            counts.append(readable_count(count=len(warnings), noun="warning"))
        return f"Wrote {self.simulation.name}: {', '.join(counts)}."

    def _connection_lines(self) -> list[str]:
        if not self.wiring.connections:
            return []
        groups: dict[tuple[str, str], list[Connection]] = {}
        for connection in self.wiring.connections:
            groups.setdefault((connection.input.model, connection.output.model), []).append(connection)
        lines = ["Connections:"]
        for (input_model, output_model), group in groups.items():
            width = max(len(connection.input.name) for connection in group)
            lines.append(f"  {input_model} <- {output_model}, {readable_count(count=len(group), noun='connection')}")
            lines += [self._connection_line(connection=connection, width=width) for connection in group]
        return lines

    def _connection_line(self, connection: Connection, width: int) -> str:
        """Like '    weatherBus_TDryBul  <-  weatherBus.TDryBul'."""
        line = f"    {connection.input.name:<{width}}  <-  {connection.output.name}"
        input_unit = input_at(models=self.models, address=connection.input).unit
        output_unit = output_at(models=self.models, address=connection.output).unit
        # nothing converts units, so a connection between two units is worth a look
        if input_unit and output_unit and input_unit != output_unit:
            return f"{line}   (the output is in {output_unit}, the input in {input_unit})"
        return line

    def _open_input_lines(self) -> list[str]:
        if not self.wiring.open_inputs:
            return []
        reasons = [f"  {open_input.input}: {self._reason_it_is_open(open_input=open_input)}" for open_input in self.wiring.open_inputs]
        return ["Not connected, so these inputs keep the start value of their FMU:", *reasons]

    def _reason_it_is_open(self, open_input: OpenInput) -> str:
        outputs = open_input.outputs_with_its_name
        of_its_size = [output for output in outputs if sizes_fit(models=self.models, input_address=open_input.input, output_address=output)]
        if len(of_its_size) > 1:
            return f"{len(of_its_size)} outputs have this name: {and_joined(texts=[str(output) for output in of_its_size])}."
        if outputs:
            input_size = value_count(interface=input_at(models=self.models, address=open_input.input))
            output_values = readable_count(count=value_count(interface=output_at(models=self.models, address=outputs[0])), noun="value")
            return f"the output {outputs[0]} has this name, but it holds {output_values} and the input takes {input_size}."
        return f"no output of another model has this name.{self._hint_for(address=open_input.input)}"

    def _hint_for(self, address: InterfaceAddress) -> str:
        outputs = [output for model in self.models if model.name != address.model for output in model.output_addresses()]
        # inputs and outputs share patterns, like Float64_discrete_input and Float64_discrete_output, which a lower cutoff would suggest
        closest = closest_name(name=address.name, known_names=[output.name for output in outputs], cutoff=0.9)
        return "" if closest is None else f" Did you mean {next(output for output in outputs if output.name == closest)}?"

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
    """Like '  feedthrough: Int32_input (Integer), since the FMI 2.0 client exchanges Real variables only.'"""
    variables = ", ".join(f"{variable.name} ({variable.type})" for variable in model.interfaces.skipped)
    client = client_type_text(client_type=model.interfaces.client_type())
    supported_type = FMUBaseConfig.supported_type(fmi_major_version=int(model.interfaces.fmi_version.split(".")[0]))
    return f"  {model.name}: {variables}, since the {client} client exchanges {supported_type} variables only."
