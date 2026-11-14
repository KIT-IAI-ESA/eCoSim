from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Iterator

from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig

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
    def of_simulation(simulation: SimulationFolder, run_options: RunOptions) -> SimulationCheck:
        with _without_the_log_of_the_readers():
            # the port of a run, which the clients get as well
            port = get_free_port()
            simulation_file = SimulationFileCheck.of_file(file=simulation.simulation_config, run_options=run_options)
            server_side = ServerSideCheck.of_simulation(simulation=simulation, run_options=run_options, simulation_file=simulation_file, port=port)
            findings = Findings()
            findings.add(simulation_file.findings)
            findings.add(server_side.findings)
            simulators = _checked_simulators(simulation=simulation, server_side=server_side, port=port, findings=findings)
            findings.warnings += by_hand_warnings(server_config_file=simulation.server_config, simulators=simulators)
        return SimulationCheck(
            findings=findings,
            simulators=simulators,
            simulator_count=None if server_side.clients is None else len(simulators),
            simulation_config=server_side.simulation_config,
            server_config=server_side.server_config,
            length_is_known=run_options.steps is not None or simulation_file.has_steps(),
        )


def _checked_simulators(simulation: SimulationFolder, server_side: ServerSideCheck, port: int, findings: Findings) -> list[CheckedSimulator]:
    if not server_side.clients:
        return []
    folders = SimulatorFolderCheck.of_folder(
        simulator_dir=simulation.simulator_dir,
        client_ids=[client.client_id for client in server_side.clients],
        simulation_config_file=simulation.simulation_config,
    )
    findings.add(folders.findings)
    simulators = []
    for client in (client for client in server_side.clients if client.client_id in folders.client_types):
        directory, client_type = folders.client_types[client.client_id]
        findings.add(
            simulator_findings(
                directory=directory,
                client_type=client_type,
                client=client,
                simulation_config=server_side.simulation_config,
                port=port,
            ),
        )
        simulators.append(
            CheckedSimulator(
                directory=directory,
                client_type=client_type,
                input_count=len(client.input_interfaces()),
                output_count=len(client.output_interfaces()),
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
