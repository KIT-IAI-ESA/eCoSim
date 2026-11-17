from dataclasses import dataclass

from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory


@dataclass(frozen=True)
class CheckedSimulator:
    directory: SimulatorDirectory
    client_type: ClientType
    input_count: int
    output_count: int

    @property
    def name(self) -> str:
        return self.directory.client_id.simulator_name
