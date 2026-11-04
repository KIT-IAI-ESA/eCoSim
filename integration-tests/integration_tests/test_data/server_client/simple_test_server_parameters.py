from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, LogicalDelay, SimulationConfig


@dataclass
class SimpleTestServerParameters:
    communication_protocol: CommunicationProtocol
    host: str
    port: int
    pace: float = field(default=1.0)
    steps: int = field(default=100)
    step_size_in_ms: int = field(default=1_000)
    simulation_start_date: datetime = field(
        default_factory=lambda: datetime(
            year=2025,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ),
    )
    clients: List[ClientSimulatorConfig] | None = field(default=None)
    database_config: DatabaseConfig | None = field(default=None)
    restore_simulation_run: bool = field(default=False)
    logical_delays: List[LogicalDelay] = field(default_factory=list)

    @staticmethod
    def of_simulation_config(
        communication_protocol: CommunicationProtocol,
        host: str,
        port: int,
        simulation_config: SimulationConfig,
    ) -> SimpleTestServerParameters:
        return SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host=host,
            port=port,
            pace=simulation_config.pace,
            steps=simulation_config.steps,
            step_size_in_ms=simulation_config.step_size_in_ms,
            simulation_start_date=simulation_config.start_date,
            clients=simulation_config.clients,
            restore_simulation_run=simulation_config.restore,
            logical_delays=simulation_config.logical_delays,
        )
