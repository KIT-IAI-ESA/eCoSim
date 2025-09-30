from dataclasses import dataclass

from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.model_interface_id import ModelInterfaceId


@dataclass(frozen=True)
class SimulatorInterfaceId:
    simulator_name: str
    model_interface_id: ModelInterfaceId

    def __str__(self) -> str:
        return f"{self.simulator_name}:{self.model_interface_id}"

    def client_id(self) -> ClientID:
        return ClientID(
            simulator_name=self.simulator_name,
            model_name=self.model_interface_id.model_name,
        )
