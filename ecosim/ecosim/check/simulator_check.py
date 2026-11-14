from __future__ import annotations

import dataclasses
from pathlib import Path

from ecosim_common.client.config.client_config import ClientConfig, ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.interface_file_keys import repeated_name_warnings, unknown_key_warnings
from ecosim_common.client.config.simulator_directory import SimulatorDirectory
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.tech.json.read_json_file import read_json_file
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig

from ecosim.check.findings import Findings, problem_of_ini_file
from ecosim.check.fmu_check import ModelCheck
from ecosim.check.model_check import model_check


def simulator_findings(
    directory: SimulatorDirectory,
    client_type: ClientType,
    client: ClientSimulatorConfig,
    simulation_config: SimulationConfig | None,
    port: int,
    before_a_run: bool,
) -> Findings:
    """What the client reads at its start and compares with the simulation config."""
    ini_file = directory.config_parser.config_file
    # the overrides that ecosim run gives every client, so the client config needs no [server]
    override = ClientConfigOverride(server_host="localhost", server_port=port, communication_protocol=CommunicationProtocol.TCP_SOCKET)
    try:
        client_config = SimpleClientConfig.of_config_parser(config_parser=directory.config_parser, config_override=override)
    except Exception as error:
        return Findings(problems=[problem_of_ini_file(error=error, ini_file=ini_file)])
    settings = client.to_server_interface_settings()
    checked_model = model_check(
        directory=directory,
        client_type=client_type,
        client_config=client_config,
        server_interface_settings=settings,
        before_a_run=before_a_run,
    )
    findings = Findings(warnings=_fmc_file_warnings(fmc_file=ini_file.parent / client_config.simulator_config().fmc_file))
    findings.add(checked_model.findings)
    findings.add(
        _mismatch_findings(directory=directory, client_config=client_config, client=client, checked_model=checked_model),
    )
    if simulation_config is not None:
        findings.problems += _required_interface_problems(directory=directory, client_config=client_config, simulation_config=simulation_config)
    return findings


def _fmc_file_warnings(fmc_file: Path) -> list[str]:
    # the client logs them, the check lists them with the other findings
    raw_interfaces = read_json_file(file=fmc_file)
    return [
        *unknown_key_warnings(raw_interfaces=raw_interfaces, fmc_file=fmc_file),
        *repeated_name_warnings(raw_interfaces=raw_interfaces, fmc_file=fmc_file),
    ]


def _mismatch_findings(
    directory: SimulatorDirectory,
    client_config: ClientConfig,
    client: ClientSimulatorConfig,
    checked_model: ModelCheck,
) -> Findings:
    """The client warns about these and runs. The names that the model check names already are left out."""
    mismatch = client_config.interfaces_config().validate_config_with_server(server_config=client.to_server_interface_settings())
    mismatch = dataclasses.replace(
        mismatch,
        inputs_not_in_fmc=[name for name in mismatch.inputs_not_in_fmc if not checked_model.names_already(name=name, fmc_names=mismatch.fmc_inputs)],
        outputs_not_in_fmc=[
            name for name in mismatch.outputs_not_in_fmc if not checked_model.names_already(name=name, fmc_names=mismatch.fmc_outputs)
        ],
    )
    return Findings(warnings=[f"{directory.path}: {line}" for line in mismatch.lines(fmc_file=client_config.simulator_config().fmc_file)])


def _required_interface_problems(directory: SimulatorDirectory, client_config: ClientConfig, simulation_config: SimulationConfig) -> list[str]:
    # the server stops the run for these
    missing = simulation_config.missing_required_interface_names(
        client_id=client_config.client_id(),
        client_interface_ids=ModelInterfaceIds.of_interface_config(client_config),
    )
    if not missing:
        return []
    fmc_file = client_config.simulator_config().fmc_file
    it_or_them = "it" if len(missing) == 1 else "them"
    return [f"{directory.path}: the simulation config marks {', '.join(missing)} as required, but {fmc_file} does not list {it_or_them}."]
