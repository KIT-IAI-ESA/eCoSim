from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, override

from ecosim_common.client.config.client_type import ClientType
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.data.server_interface_settings import (
    ServerInterfaceSettings,
)
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.optional_access import if_exists


class ClientConfig(ABC):
    logger = ESPLogger("ClientConfig")

    __protocol_version = "2.0"

    @abstractmethod
    def simulator_config(self) -> SimulatorConfig:
        pass

    @abstractmethod
    def server_config(self) -> ServerConfig:
        pass

    @abstractmethod
    def interfaces_config(self) -> ClientInterfaceConfig:
        pass

    @abstractmethod
    def type(self) -> ClientType:
        pass

    @abstractmethod
    def communication_protocol(self) -> CommunicationProtocol:
        pass

    def client_id(self) -> ClientID:
        return ClientID(
            simulator_name=self.simulator_config().simulator_name,
            model_name=self.simulator_config().model_name,
        )

    def meta_data(self) -> ClientMetaData:
        return ClientMetaData(
            version=ClientConfig.__protocol_version,
            simulator_name=self.simulator_config().simulator_name,
            model_name=self.simulator_config().model_name,
        )

    def print_to_info(self) -> None:
        GlobalLogger.print_values(
            header="CLIENT CONFIG",
            value_pairs={
                "Simulator name": self.simulator_config().simulator_name,
                "Model name": self.simulator_config().model_name,
                "Simulation type": self.type(),
                "Server address": self.server_config().server_address,
                "Image renderer port": self.server_config().image_renderer_port if self.server_config().image_renderer_port else "N/A",
                "Provided interfaces": self.interfaces_config().interfaces,
            },
        )

    @abstractmethod
    def as_config_file_content(self) -> str:
        pass


@dataclass(frozen=True)
class SimpleClientConfig(ClientConfig):
    _server_config: ServerConfig
    _simulator_config: SimulatorConfig
    _interfaces_config: ClientInterfaceConfig
    _extra_sections: List[str]

    @staticmethod
    def of_config_parser(
        config_parser: ConfigParser,
        config_override: ClientConfigOverride | None = None,
    ) -> SimpleClientConfig:
        simulator_config = SimulatorConfig.of_config_parser(config_parser)
        return SimpleClientConfig(
            _server_config=ServerConfig.of_config_parser(
                config_parser,
                config_override,
            ),
            _simulator_config=simulator_config,
            _interfaces_config=ClientInterfaceConfig.of_simulator_config(
                config_path=config_parser.config_file.parent,
                simulator_config=simulator_config,
            ),
            # currently these are only copied from original client-config
            _extra_sections=config_parser.extract_extra_sections(),
        )

    @override
    def simulator_config(self) -> SimulatorConfig:
        return self._simulator_config

    @override
    def server_config(self) -> ServerConfig:
        return self._server_config

    @override
    def interfaces_config(self) -> ClientInterfaceConfig:
        return self._interfaces_config

    @override
    def type(self) -> ClientType:
        return self._simulator_config.type

    @override
    def communication_protocol(self) -> CommunicationProtocol:
        return self._server_config.communication_protocol

    @override
    def as_config_file_content(self) -> str:
        extra_sections_str = "\n\n".join(s for s in self._extra_sections if s)

        return (
            f"""
{self.server_config().as_string()}

{self.simulator_config().as_string()}

{extra_sections_str}
        """
        ).strip()


@dataclass(frozen=True)
class ServerConfig:
    server_address: ConnectionAddress
    communication_protocol: CommunicationProtocol
    image_renderer_port: int | None = None

    def as_string(self) -> str:
        return (
            f"""
[server]
ip = {self.server_address.ip}
port = {self.server_address.port}
communication_protocol = {self.communication_protocol.serialized}
        """
        ).strip()

    @staticmethod
    def of_config_parser(
        config: ConfigParser,
        config_override: ClientConfigOverride | None = None,
    ) -> ServerConfig:
        ip: str = if_exists(config_override).server_host or config.get_string(
            "server",
            "ip",
        )
        port: int = if_exists(config_override).server_port or config.get_int(
            "server",
            "port",
        )
        communication_protocol = if_exists(config_override).communication_protocol or config.get_enum(
            CommunicationProtocol,
            "server",
            "communication_protocol",
            CommunicationProtocol.TCP_SOCKET,
        )
        return ServerConfig(
            server_address=ConnectionAddress(ip=ip, port=port),
            communication_protocol=communication_protocol,
            image_renderer_port=if_exists(config_override).image_renderer_port,
        )


@dataclass(frozen=True)
class SimulatorConfig:
    simulator_name: str
    model_name: str
    fmc_file: str
    type: ClientType

    def as_string(self) -> str:
        return (
            f"""
[simulator]
simulator_name = {self.simulator_name}
model_name = {self.model_name}
fmc_file = {self.fmc_file}
type = {self.type.serialized}
        """
        ).strip()

    @staticmethod
    def of_config_parser(
        config: ConfigParser,
    ) -> SimulatorConfig:
        return SimulatorConfig(
            simulator_name=config.get_string(
                "simulator",
                "simulator_name",
            ),
            model_name=config.get_string(
                "simulator",
                "model_name",
            ),
            type=ClientType.of_string(
                config.get_string(
                    "simulator",
                    "type",
                ),
            ),
            fmc_file=config.get_string_array(
                "simulator",
                "fmc_file",
            )[0],
        )


@dataclass(frozen=True)
class ClientInterfaceConfig:
    interfaces: List[ModelInterfaceClient]

    @staticmethod
    def of_simulator_config(
        simulator_config: SimulatorConfig,
        config_path: Path = Path("."),
    ) -> ClientInterfaceConfig:
        interfaces: List[ModelInterfaceClient] = []
        if not simulator_config.fmc_file:
            raise FileNotFoundError("No FMC file detected in config.")
        fmc_file_absolute = config_path / simulator_config.fmc_file
        try:
            with open(
                fmc_file_absolute,
                "r",
            ) as fmc_file:
                fmc_json = json.load(fmc_file)
                input_interfaces = fmc_json.get("inputs", [])
                output_interfaces = fmc_json.get("outputs", [])
                for input_interface in input_interfaces:
                    if not input_interface["name"]:
                        ClientConfig.logger.warning("There is an input interface without a name in file %s: %s", fmc_file_absolute, input_interface)
                        continue
                    interfaces.append(
                        ModelInterfaceClient.of_json_client_config(
                            model_interface_id=ModelInterfaceId(
                                model_name=simulator_config.model_name,
                                interface=input_interface["name"],
                            ),
                            interface=input_interface,
                            interface_type=InterfaceType.INPUT,
                        ),
                    )
                for output_interface in output_interfaces:
                    interfaces.append(
                        ModelInterfaceClient.of_json_client_config(
                            model_interface_id=ModelInterfaceId(
                                model_name=simulator_config.model_name,
                                interface=output_interface["name"],
                            ),
                            interface=output_interface,
                            interface_type=InterfaceType.OUTPUT,
                        ),
                    )
                    if not output_interface["name"]:
                        ClientConfig.logger.warning("There is an output interface without a name in file %s: %s", fmc_file_absolute, output_interface)
                        continue
        except FileNotFoundError:
            error_message = f"Can not load fmc file {simulator_config.fmc_file}"
            ClientConfig.logger.error(error_message)
            raise FileNotFoundError(error_message)
        except json.JSONDecodeError as e:
            error_message = f"Can not parse fmc file {fmc_file_absolute} - invalid json"
            ClientConfig.logger.error(error_message)
            raise json.JSONDecodeError(
                error_message,
                e.doc,
                e.pos,
            )
        return ClientInterfaceConfig(interfaces=interfaces)

    def all_interfaces_to_protocol_json_string(self) -> str:
        return json.dumps(self.interfaces, default=asdict)

    def _required_input_interface_names(self) -> List[str]:
        return [interface.name for interface in self.interfaces if interface.required and interface.type == InterfaceType.INPUT]

    def input_interface_names(self, only_required: bool = False) -> List[str]:
        if only_required:
            return [interface.name for interface in self.interfaces if interface.type == InterfaceType.INPUT and interface.required]
        return [interface.name for interface in self.interfaces if interface.type == InterfaceType.INPUT]

    def output_interface_names(self) -> List[str]:
        return [interface.name for interface in self.interfaces if interface.type == InterfaceType.OUTPUT]

    def validate_config_with_server(
        self,
        server_config: ServerInterfaceSettings,
    ) -> bool:
        return (
            self._all_required_inputs_are_matched_by_actual(server_config.inputs)
            and self._all_actual_inputs_are_in_config(server_config.inputs)
            and self._all_actual_outputs_are_in_config(server_config.outputs)
        )

    def _all_required_inputs_are_matched_by_actual(
        self,
        actual_inputs: List[InterfaceId],
    ) -> bool:
        return all(required_input in actual_inputs for required_input in self._required_input_interface_names())

    def _all_actual_inputs_are_in_config(
        self,
        actual_inputs: List[InterfaceId],
    ) -> bool:
        return all(actual_input in self.input_interface_names() for actual_input in actual_inputs)

    def _all_actual_outputs_are_in_config(
        self,
        actual_outputs: List[InterfaceId],
    ) -> bool:
        return all(actual_output in self.output_interface_names() for actual_output in actual_outputs)


@dataclass
class ClientConfigOverride:
    server_host: str | None = None
    server_port: int | None = None
    image_renderer_port: int | None = None
    communication_protocol: CommunicationProtocol | None = None
