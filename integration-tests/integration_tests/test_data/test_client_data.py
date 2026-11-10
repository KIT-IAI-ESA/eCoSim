from __future__ import annotations

import dataclasses
from typing import List

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
    InterfaceValue,
)
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from ecosim_test_common.test_data.test_model_interface import TestModelInterface


@dataclasses.dataclass
class TestClientData:
    __test__ = False

    simulator_name: str
    model_name: str
    interfaces: List[TestModelInterface]

    @staticmethod
    def with_output(
        simulator_name: str,
        model_name: str,
        output_name: str,
    ) -> TestClientData:
        client_data = TestClientData(simulator_name=simulator_name, model_name=model_name, interfaces=[])
        client_data.add_interface(interface_name=output_name, unit="float64", interface_type=InterfaceType.OUTPUT)
        return client_data

    def add_interface(
        self,
        interface_name: str,
        unit: str,
        interface_type: InterfaceType,
        connected_interface: TestModelInterface | None = None,
    ) -> TestModelInterface:
        interface = TestModelInterface(
            simulator_name=self.simulator_name,
            model_name=self.model_name,
            interface_name=interface_name,
            unit=unit,
            interface_type=interface_type,
            connected_interface=connected_interface,
        )
        if connected_interface is not None:
            connected_interface.connected_interface = interface
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
            interfaces=[interface.to_model_interface_server() for interface in self.interfaces],
        )

    def to_client_interface_config(self) -> ClientInterfaceConfig:
        return ClientInterfaceConfig(
            interfaces=[interface.to_model_interface_client() for interface in self.interfaces],
        )

    def interface_protocol_value_of(
        self,
        interface_name: str,
        value: InterfaceValue,
    ) -> ProtocolInterfaceValue:
        for interface in self.interfaces:
            if interface.interface_name == interface_name:
                return interface.to_protocol_interface_value(value)
        available = ", ".join(i.interface_name for i in self.interfaces)
        raise ValueError(
            f"Interface '{interface_name}' not found. Available interfaces: [{available}]",
        )
