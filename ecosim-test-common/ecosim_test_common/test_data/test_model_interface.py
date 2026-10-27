from __future__ import annotations

import dataclasses

from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
    InterfaceValue,
)
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import (
    ModelInterfaceServer,
    ConnectedToData,
)
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId


@dataclasses.dataclass
class TestModelInterface:
    simulator_name: str
    model_name: str
    interface_name: str
    unit: str
    interface_type: InterfaceType
    connected_interface: TestModelInterface | None = None

    def to_simulator_interface_id(self) -> SimulatorInterfaceId:
        return SimulatorInterfaceId(
            simulator_name=self.simulator_name,
            model_interface_id=ModelInterfaceId(
                model_name=self.model_name,
                interface=self.interface_name,
            ),
        )

    def to_model_interface_server(self) -> ModelInterfaceServer:
        connected_to = []
        if self.connected_interface is not None:
            connected_to = [self.connected_interface.to_connected_data()]

        return ModelInterfaceServer(
            simulator_interface_id=self.to_simulator_interface_id(),
            name=self.interface_name,
            unit=self.unit,
            description=f"Interface {self.interface_name} of {self.model_name}",
            interface_type=self.interface_type,
            required=True,
            connected_to=connected_to,
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
        value: InterfaceValue,
    ) -> ProtocolInterfaceValue:
        return ProtocolInterfaceValue(
            name=self.interface_name,
            value=value,
        )

    def to_connected_data(self) -> ConnectedToData:
        return ConnectedToData(
            simulator_interface_id=self.to_simulator_interface_id(),
            delay_path=[],
        )
