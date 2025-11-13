import dataclasses

from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
    InterfaceValueType,
)
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId


@dataclasses.dataclass
class TestModelInterface:
    simulator_name: str
    model_name: str
    interface_name: str
    unit: str
    interface_type: InterfaceType

    def to_simulator_interface_id(self) -> SimulatorInterfaceId:
        return SimulatorInterfaceId(
            simulator_name=self.simulator_name,
            model_interface_id=ModelInterfaceId(
                model_name=self.model_name,
                interface=self.interface_name,
            ),
        )

    def to_model_interface_server(self) -> ModelInterfaceServer:
        return ModelInterfaceServer(
            simulator_interface_id=self.to_simulator_interface_id(),
            name=self.interface_name,
            unit=self.unit,
            description=f"Interface {self.interface_name} of {self.model_name}",
            interface_type=self.interface_type,
            required=True,
            connected_to=[],
        )

    def to_model_interface_client(self) -> ModelInterfaceClient:
        return ModelInterfaceClient(
            model_interface_id=ModelInterfaceId(
                model_name=self.model_name,
                interface=self.interface_name,
            ),
            name=self.interface_name,
            unit=self.unit,
            description=f"Interface {self.interface_name} of {self.model_name}",
            required=True,
            type=self.interface_type,
        )

    def to_protocol_interface_value(
        self,
        value: InterfaceValueType,
    ) -> ProtocolInterfaceValue:
        return ProtocolInterfaceValue(
            name=self.interface_name,
            value=value,
        )
