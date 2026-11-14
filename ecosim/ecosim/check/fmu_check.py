from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fmpy
from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.config.interface_mismatch import INTERFACE_NAME_CUTOFF
from ecosim_common.client.config.simulator_directory import SimulatorDirectory
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.tech.close_name import closest_name
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterfaces
from ecosim_common_fmpy.config.start_values import StartValues
from ecosim_common_fmpy.tech.fmu_platforms import binary_platforms
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from fmpy.model_description import ModelDescription

from ecosim.check.findings import Findings, problem_of, problem_of_ini_file


@dataclass(frozen=True)
class ModelCheck:
    findings: Findings = field(default_factory=Findings)
    # the interfaces of the simulation config that the model lacks
    missing_interfaces: list[str] = field(default_factory=list)
    # the names of the .fmc file that the model lacks, often a typo
    fmc_names_not_in_the_model: list[str] = field(default_factory=list)

    def names_already(self, name: str, fmc_names: list[str]) -> bool:
        """Whether the findings name the interface, or the misspelt .fmc name a hint would suggest."""
        suggested = closest_name(name=name, known_names=fmc_names, cutoff=INTERFACE_NAME_CUTOFF)
        return name in self.missing_interfaces or suggested in self.fmc_names_not_in_the_model


def fmu_check(directory: SimulatorDirectory, client_config: ClientConfig, server_interface_settings: ServerInterfaceSettings) -> ModelCheck:
    """What the FMU client checks at its start and when the server sends the simulation config."""
    ini_file = directory.config_parser.config_file
    try:
        fmu_config = FMUBaseConfig.of_config_parser(directory.config_parser)
        # an FMI version no client runs, or an FMU without its co-simulation part
        FMUInterfaces.of_fmu_file(fmu_file=fmu_config.fmu_file)
        model_description = read_model_description(file=fmu_config.fmu_file)
    except Exception as error:
        return ModelCheck(findings=Findings(problems=[problem_of_ini_file(error=error, ini_file=ini_file)]))
    findings = Findings(problems=_platform_problems(fmu_file=fmu_config.fmu_file))
    findings.add(
        _interface_findings(
            fmu_config=fmu_config,
            model_description=model_description,
            client_config=client_config,
            settings=server_interface_settings,
            directory=directory,
        ),
    )
    findings.add(
        _start_value_findings(
            fmu_config=fmu_config,
            model_description=model_description,
            client_config=client_config,
            settings=server_interface_settings,
            ini_file=ini_file,
        ),
    )
    return _with_the_names_not_in_the_model(
        findings=findings,
        model_description=model_description,
        client_config=client_config,
        settings=server_interface_settings,
    )


def _with_the_names_not_in_the_model(
    findings: Findings,
    model_description: ModelDescription,
    client_config: ClientConfig,
    settings: ServerInterfaceSettings,
) -> ModelCheck:
    interfaces = client_config.interfaces_config()
    fmc_inputs, fmc_outputs = FMUBaseConfig.missing_interfaces(
        model_description=model_description,
        input_names=interfaces.input_interface_names(),
        output_names=interfaces.output_interface_names(),
    )
    inputs, outputs = FMUBaseConfig.missing_interfaces(
        model_description=model_description,
        input_names=settings.inputs,
        output_names=settings.outputs,
    )
    return ModelCheck(findings=findings, missing_interfaces=[*inputs, *outputs], fmc_names_not_in_the_model=[*fmc_inputs, *fmc_outputs])


def _platform_problems(fmu_file: Path) -> list[str]:
    platforms = binary_platforms(fmu_file=fmu_file)
    if fmpy.platform in platforms:
        return []
    only_for = f"for this computer ({fmpy.platform}), only for {', '.join(platforms)}" if platforms else "at all"
    return [f"{fmu_file} has no binary {only_for}. Get an FMU built for {fmpy.platform}."]


def _interface_findings(
    fmu_config: FMUBaseConfig,
    model_description: ModelDescription,
    client_config: ClientConfig,
    settings: ServerInterfaceSettings,
    directory: SimulatorDirectory,
) -> Findings:
    interfaces = client_config.interfaces_config()
    try:
        # the client stops at its start for these
        fmu_config.ensure_model_runs_interfaces(
            model_description=model_description,
            input_names=interfaces.input_interface_names(),
            output_names=interfaces.output_interface_names(),
            fmi_major_version=model_description.fmiMajorVersion,
        )
    except (ValueError, TypeError) as error:
        return Findings(problems=[problem_of(error=error, file=directory.path / client_config.simulator_config().fmc_file)])
    reason = fmu_config.reason_the_model_cannot_run(
        model_description=model_description,
        input_names=settings.inputs,
        output_names=settings.outputs,
        fmi_major_version=model_description.fmiMajorVersion,
    )
    return Findings(problems=[] if reason is None else [f"{directory.path}: {reason}"])


def _start_value_findings(
    fmu_config: FMUBaseConfig,
    model_description: ModelDescription,
    client_config: ClientConfig,
    settings: ServerInterfaceSettings,
    ini_file: Path,
) -> Findings:
    fmc_inputs = client_config.interfaces_config().input_interface_names()
    problems = StartValues.problems_of(texts=fmu_config.start_value_texts, model_description=model_description, input_names=fmc_inputs)
    # the client refuses only a start value of an input of the .fmc file
    connected = [name for name in fmu_config.start_value_texts if name in settings.inputs and name not in fmc_inputs]
    return Findings(
        problems=[f"{ini_file}: [start_values] {problem}" for problem in problems],
        warnings=[
            f"{ini_file}: the start value of {name} has no effect, since the simulation config connects the input {name}." for name in connected
        ],
    )
