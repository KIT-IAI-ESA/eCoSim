from dataclasses import dataclass

from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory


@dataclass(frozen=True)
class CheckedSimulator:
    """A simulator of the simulation with its folder and the client that runs its model."""

    directory: SimulatorDirectory
    client_type: ClientType
    # as the simulation config connects them, which is what a run uses
    input_count: int
    output_count: int

    @property
    def name(self) -> str:
        return self.directory.client_id.simulator_name
