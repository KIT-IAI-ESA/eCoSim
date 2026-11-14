from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Iterator

from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig

from ecosim.check.by_hand_check import by_hand_warnings
from ecosim.check.checked_simulator import CheckedSimulator
from ecosim.check.findings import Findings
from ecosim.check.server_side_check import ServerSideCheck
from ecosim.check.simulation_file_check import SimulationFileCheck
from ecosim.check.simulator_check import simulator_findings
from ecosim.check.simulator_folder_check import SimulatorFolderCheck
from ecosim.simulation_folder import SimulationFolder
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class SimulationCheck:
    """What a run reads, checked with the readers of the server and the clients."""

    findings: Findings
    simulators: list[CheckedSimulator]
    # the simulators of the table, None if simulation.json cannot be read
    simulator_count: int | None
    simulation_config: SimulationConfig | None
    server_config: ServerConfig | None
    # from --steps, --duration or setup.steps
    length_is_known: bool

    @staticmethod
    def of_simulation(simulation: SimulationFolder, run_options: RunOptions, before_a_run: bool = False) -> SimulationCheck:
        """Before a run, a Pyro5 object that nothing listens on is a problem, as the run would fail."""
        with _without_the_log_of_the_readers():
            # the port of a run, which the clients get as well
            port = get_free_port()
            simulation_file = SimulationFileCheck.of_file(file=simulation.simulation_config, run_options=run_options)
            server_side = ServerSideCheck.of_simulation(simulation=simulation, run_options=run_options, simulation_file=simulation_file, port=port)
            findings = Findings()
            findings.add(simulation_file.findings)
            findings.add(server_side.findings)
            simulators = _checked_simulators(simulation=simulation, server_side=server_side, port=port, findings=findings, before_a_run=before_a_run)
            findings.warnings += by_hand_warnings(server_config_file=simulation.server_config, simulators=simulators)
        return SimulationCheck(
            findings=findings,
            simulators=simulators,
            simulator_count=None if server_side.clients is None else len(simulators),
            simulation_config=server_side.simulation_config,
            server_config=server_side.server_config,
            length_is_known=run_options.steps is not None or simulation_file.has_steps(),
        )


def simulators_of(simulation: SimulationFolder, clients: list[ClientSimulatorConfig]) -> tuple[list[CheckedSimulator], Findings]:
    """The folder and the client of each simulator, all that a run needs to start the clients."""
    folders = SimulatorFolderCheck.of_folder(
        simulator_dir=simulation.simulator_dir,
        client_ids=[client.client_id for client in clients],
        simulation_config_file=simulation.simulation_config,
    )
    simulators = [
        CheckedSimulator(
            directory=folders.client_types[client.client_id][0],
            client_type=folders.client_types[client.client_id][1],
            input_count=len(client.input_interfaces()),
            output_count=len(client.output_interfaces()),
        )
        for client in clients
        if client.client_id in folders.client_types
    ]
    return simulators, folders.findings


def _checked_simulators(
    simulation: SimulationFolder,
    server_side: ServerSideCheck,
    port: int,
    findings: Findings,
    before_a_run: bool,
) -> list[CheckedSimulator]:
    if not server_side.clients:
        return []
    simulators, folder_findings = simulators_of(simulation=simulation, clients=server_side.clients)
    findings.add(folder_findings)
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
    return simulators


@contextlib.contextmanager
def _without_the_log_of_the_readers() -> Iterator[None]:
    """The check lists what the readers find, and with --debug they would name defaults that the run overrides."""
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)
