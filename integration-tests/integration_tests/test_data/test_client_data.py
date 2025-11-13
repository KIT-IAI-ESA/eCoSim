import dataclasses
from typing import List

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
    InterfaceValueType,
)
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.test_data.test_model_interface import TestModelInterface


@dataclasses.dataclass
class TestClientData:
    simulator_name: str
    model_name: str
    interfaces: List[TestModelInterface]

    def add_interface(
        self,
        interface_name: str,
        unit: str,
        interface_type: InterfaceType,
    ) -> TestModelInterface:
        interface = TestModelInterface(
            simulator_name=self.simulator_name,
            model_name=self.model_name,
            interface_name=interface_name,
            unit=unit,
            interface_type=interface_type,
        )
        self.interfaces.append(interface)
        return interface

    def to_client_simulator_config(self) -> ClientSimulatorConfig:
        return ClientSimulatorConfig(
            simulator_name=self.simulator_name,
            model_name=self.model_name,
            client_id=ClientID(
                model_name=self.model_name,
                simulator_name=self.simulator_name,
            ),
            interfaces=[
                interface.to_model_interface_server() for interface in self.interfaces
            ],
        )

    def to_client_interface_config(self) -> ClientInterfaceConfig:
        return ClientInterfaceConfig(
            interfaces=[
                interface.to_model_interface_client() for interface in self.interfaces
            ],
        )

    def interface_protocol_value_of(  # type: ignore[empty-body]
        self,
        interface_name: str,
        value: InterfaceValueType,
    ) -> ProtocolInterfaceValue:
        pass
