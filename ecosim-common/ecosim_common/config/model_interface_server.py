from __future__ import annotations
from typing import List, Any

from dataclasses import dataclass

from ecosim_common.config import config_parser
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_common.tech.logger.logger import ESPLogger


class ModelInterfaceServer:
    _logger = ESPLogger("ModelInterfaceServer")

    @staticmethod
    def of_config_json(
            simulator_name: str,
            model_name: str,
            raw_interface: dict[str, Any],
            raw_simulators: List[dict[str, str]],
    ) -> ModelInterfaceServer:
        interface_name = raw_interface['name']
        if not interface_name:
            raise RuntimeError(f"Interface name is required: Interface: {raw_interface} || Simulator: {simulator_name} || Model: {model_name}")
        interface_type = raw_interface['type']
        if not interface_type:
            raise RuntimeError(f"Interface type is required: Interface: {raw_interface} || Simulator: {simulator_name} || Model: {model_name}")
        return ModelInterfaceServer(
            simulator_interface_id=SimulatorInterfaceId(simulator_name=simulator_name,
                                                        model_interface_id=ModelInterfaceId(model_name=model_name,
                                                                                            interface=interface_name)),
            name=interface_name,
            unit=raw_interface.get('unit'),
            description=raw_interface.get('description'),
            interface_type=InterfaceType.of(interface_type),
            required=config_parser.ConfigParser.config_string_to_bool(raw_interface.setdefault('required',
                                                                                               'false')),
            connected_to=ModelInterfaceServer._get_connected_to(raw_interface.get('connected_to'),
                                                                raw_simulators)
        )

    def __init__(self,
                 simulator_interface_id: SimulatorInterfaceId,
                 name: str,
                 unit: str | None,
                 description: str | None,
                 interface_type: InterfaceType | None,
                 required: bool | None,
                 connected_to: List[ConnectedToData],
                 ):
        self.simulator_interface_id: SimulatorInterfaceId = simulator_interface_id
        self.name = name
        self.unit = unit
        self.description = description
        self.type = interface_type
        self.required = required
        self.connected_to: List[ConnectedToData] = connected_to

    @property
    def model_interface_id(self) -> ModelInterfaceId:
        return self.simulator_interface_id.model_interface_id

    def interface_id(self) -> InterfaceId:
        return self.simulator_interface_id.model_interface_id.interface

    @staticmethod
    def _get_connected_to(raw_connected_to: List[dict[str, str]] | None,
                          raw_simulators: List[dict[str, str]],
                          ) -> List[ConnectedToData]:
        if not raw_connected_to:
            return []
        result: List[ConnectedToData] = []
        if len(raw_connected_to) != 1:
            raise RuntimeError(f"Expected 1 connected_to, got {len(raw_connected_to)}")
        connection = raw_connected_to[0]
        simulator_index_string = connection.get('simulator')
        if not simulator_index_string:
            raise RuntimeError(f"Simulator index is required: {connection}")
        simulator_index = int(simulator_index_string)
        simulator = raw_simulators[simulator_index]
        simulator_name = simulator.get("name")
        if not simulator_name:
            raise RuntimeError(f"Simulator name is required: {connection}")
        simulator_model_name = simulator.get("model")
        if not simulator_model_name:
            raise RuntimeError(f"Simulator model name is required: {connection}")
        model_interface_name = connection.get("interface")
        if not model_interface_name:
            raise RuntimeError(f"Interface name is required: {connection}")
        result.append(
            ConnectedToData(
                simulator_interface_id=SimulatorInterfaceId(simulator_name=simulator_name,
                                                            model_interface_id=ModelInterfaceId(
                                                                model_name=simulator_model_name,
                                                                interface=model_interface_name)),
                delay_path=connection.get('delay_path', []),  # type: ignore
            )
        )
        return result

    def __eq__(self,
               other: Any,
               ) -> bool:
        if isinstance(other,
                      ModelInterfaceServer):
            return self.model_interface_id == other.model_interface_id
        return False


@dataclass(frozen=True)
class ConnectedToData:
    simulator_interface_id: SimulatorInterfaceId
    delay_path: List[str]
