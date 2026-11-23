from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Iterator

from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig

from ecosim.check.checked_simulator import CheckedSimulator
from ecosim.check.findings import Findings
from ecosim.check.manual_start_check import manual_start_warnings
from ecosim.check.server_side_check import ServerSideCheck
from ecosim.check.simulation_config_check import SimulationConfigCheck
from ecosim.check.simulator_check import simulator_findings
from ecosim.check.simulator_directory_check import SimulatorDirectoryCheck
from ecosim.simulation_directory import SimulationDirectory
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class SimulationCheck:
    findings: Findings
    simulators: list[CheckedSimulator]
    # None if simulation.json cannot be read
    simulator_count: int | None
    simulation_config: SimulationConfig | None
    server_config: ServerConfig | None
    length_is_known: bool

    @staticmethod
    def of_simulation(simulation: SimulationDirectory, run_options: RunOptions, before_a_run: bool = False) -> SimulationCheck:
        with _without_the_log_of_the_readers():
            port = get_free_port()
            simulation_config_check = SimulationConfigCheck.of_file(file=simulation.simulation_config, run_options=run_options)
            server_side = ServerSideCheck.of_simulation(
                simulation=simulation,
                run_options=run_options,
                simulation_config_check=simulation_config_check,
                port=port,
            )
            simulators, findings_of_the_simulators = _checked_simulators(
                simulation=simulation,
                server_side=server_side,
                port=port,
                before_a_run=before_a_run,
            )
            findings = Findings()
            findings.add(simulation_config_check.findings)
            findings.add(server_side.findings)
            findings.add(findings_of_the_simulators)
            findings.warnings += manual_start_warnings(server_config_file=simulation.server_config, simulators=simulators)
        return SimulationCheck(
            findings=findings,
            simulators=simulators,
            simulator_count=None if server_side.clients is None else len(simulators),
            simulation_config=server_side.simulation_config,
            server_config=server_side.server_config,
            length_is_known=run_options.steps is not None or simulation_config_check.has_steps(),
        )


def simulators_of(simulation: SimulationDirectory, clients: list[ClientSimulatorConfig]) -> tuple[list[CheckedSimulator], Findings]:
    directories = SimulatorDirectoryCheck.of_directory(
        simulator_dir=simulation.simulator_dir,
        client_ids=[client.client_id for client in clients],
        simulation_config_file=simulation.simulation_config,
    )
    simulators = [
        CheckedSimulator(
            directory=directories.client_types[client.client_id][0],
            client_type=directories.client_types[client.client_id][1],
            input_count=len(client.input_interfaces()),
            output_count=len(client.output_interfaces()),
        )
        for client in clients
        if client.client_id in directories.client_types
    ]
    return simulators, directories.findings


def _checked_simulators(
    simulation: SimulationDirectory,
    server_side: ServerSideCheck,
    port: int,
    before_a_run: bool,
) -> tuple[list[CheckedSimulator], Findings]:
    if not server_side.clients:
        return [], Findings()
    simulators, findings = simulators_of(simulation=simulation, clients=server_side.clients)
    clients = {client.client_id: client for client in server_side.clients}
    for simulator in simulators:
        findings.add(
            simulator_findings(
                directory=simulator.directory,
                client_type=simulator.client_type,
                client=clients[simulator.directory.client_id],
                simulation_config=server_side.simulation_config,
                port=port,
                before_a_run=before_a_run,
            ),
        )
    return simulators, findings


@contextlib.contextmanager
def _without_the_log_of_the_readers() -> Iterator[None]:
    # with --debug the readers would log defaults that the run overrides
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)
