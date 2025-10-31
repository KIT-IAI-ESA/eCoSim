from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Set, ClassVar, Any

from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.config.client_id import ClientID


@dataclass(frozen=True)
class SimulationConfig:
    logger: ClassVar[ESPLogger] = ESPLogger("SimulationConfig")

    clients: List[ClientSimulatorConfig]
    steps: int
    step_size_in_ms: int
    start_date: datetime
    logical_delays: List[LogicalDelay]
    pace: float = 1.0

    @staticmethod
    def of_config_file_and_params(
            simulation_config_file: Path,
            steps: int,
            step_size_override: int | None = None,
            pace: float = 1.0,
    ) -> SimulationConfig:
        config = SimulationConfig._load_config(simulation_config_file)
        clients: List[ClientSimulatorConfig] = SimulationConfig._load_all_clients(config)
        logical_delays: List[LogicalDelay] = [
            LogicalDelay.of_config(logical_delay, logical_delay_index, clients) for
            logical_delay_index, logical_delay in
            enumerate(config["logical_delays"])
        ]
        return SimulationConfig(
            clients=clients,
            steps=steps,
            step_size_in_ms=step_size_override if step_size_override else int(config["setup"]["delta_t"]),
            pace=pace,
            start_date=datetime.fromisoformat(
                config["setup"].get("start_date", "2024-01-01T00:00:00.000Z"),
            ),
            logical_delays=logical_delays,
        )

    def __post_init__(self) -> None:
        self._validate_clients(clients=self.clients)

    def _validate_clients(
        self,
        clients: List[ClientSimulatorConfig],
    ) -> None:
        all_client_ids = []
        for client in clients:
            if client.client_id in all_client_ids:
                raise Exception(f"Duplicate simulator id in config: {client.client_id}")
            all_client_ids.append(client.client_id)

    @staticmethod
    def _load_all_clients(server_config: dict[str, Any]) -> List[ClientSimulatorConfig]:
        clients: List[ClientSimulatorConfig] = []
        for block in server_config["simulators"]:
            clients.append(ClientSimulatorConfig.of_configs(block, server_config))
        return clients

    @staticmethod
    def _load_config(simulation_config_file: Path) -> dict[str, Any]:
        with open(simulation_config_file) as file:
            config: dict[str, Any] = json.load(file)
            return config

    def client_simulator_config_for(
        self,
        client_id: ClientID,
    ) -> ClientSimulatorConfig | None:
        for client in self.clients:
            if client.model_name == client_id.model_name and client.simulator_name == client_id.simulator_name:
                return client
        SimulationConfig.logger.warning(f"Cannot find simulator config for client {client_id}")
        return None

    def validate_interfaces(
        self,
        client_id: ClientID,
        client_interface_ids: ModelInterfaceIds,
    ) -> bool:
        client_simulation_config = self.client_simulator_config_for(client_id)
        if client_simulation_config is None:
            SimulationConfig.logger.error(f"Client {client_id} does not have a config.")
            return False
        defined_interfaces = client_simulation_config.interfaces

        for defined_interface in defined_interfaces:
            if defined_interface.required and defined_interface.model_interface_id not in client_interface_ids.interfaces:
                SimulationConfig.logger.error(
                    f"Client {client_id} does not contain required interface {defined_interface.name}",
                )
                return False
        return True

    def connected_input_interfaces_by_client_and_interface_name(
        self,
        client_id: ClientID,
        interface_name: str,
    ) -> Tuple[SimulatorInterfaceId, ...]:
        client_config = self.client_simulator_config_for(client_id)
        if client_config is None:
            raise Exception(f"Client {client_id} does not have a config.")
        simulator_interface_id = SimulatorInterfaceId(
            simulator_name=client_config.simulator_name,
            model_interface_id=ModelInterfaceId(
                model_name=client_config.model_name,
                interface=interface_name,
            ),
        )
        return self.connected_output_interfaces_by_simulator_interface_id(simulator_interface_id)

    def connected_output_interfaces_by_simulator_interface_id(
        self,
        simulator_interface_id: SimulatorInterfaceId,
    ) -> Tuple[SimulatorInterfaceId, ...]:
        result: Set[SimulatorInterfaceId] = set([])
        for client in self.clients:
            for interface in client.interfaces:
                if interface.type != InterfaceType.INPUT:
                    continue
                for connected_data in interface.connected_to:
                    if connected_data.simulator_interface_id == simulator_interface_id:
                        result.add(interface.simulator_interface_id)
        return tuple(result)

    def date_time_for_step(
        self,
        step: float,
    ) -> datetime:
        return self.start_date + timedelta(milliseconds=step * self.step_size_in_ms)

    def print_for_start_up(self) -> None:
        GlobalLogger.print_values(
            header="SIMULATION CONFIG",
            value_pairs={
                "Step size (in ms)": self.step_size_in_ms,
                "Steps": self.steps,
                "Simulated start time": self.start_date,
                "Expected clients": [client.client_id for client in self.clients],
            },
        )


@dataclass(frozen=True)
class ClientSimulatorConfig:
    simulator_name: str
    model_name: str
    interfaces: List[ModelInterfaceServer]
    client_id: ClientID

    @staticmethod
    def of_configs(
            config: dict[str, Any],
            server_config: dict[str, Any],
    ) -> ClientSimulatorConfig:
        simulator_name = config["name"]
        model_name = config["model"]
        interfaces: List[ModelInterfaceServer] = []
        for interface in config["interfaces"]:
            interfaces.append(
                ModelInterfaceServer.of_config_json(
                simulator_name=simulator_name,
                model_name=model_name,
                raw_interface=interface,
                raw_simulators=server_config["simulators"],
                ),
            )
        return ClientSimulatorConfig(
            simulator_name=simulator_name,
            model_name=model_name,
            interfaces=interfaces,
            client_id=ClientID(
                model_name,
                simulator_name,
            ),
        )

    def to_server_interface_settings(self) -> ServerInterfaceSettings:
        inputs = [interface.interface_id() for interface in self.interfaces if interface.type == InterfaceType.INPUT]
        outputs = [interface.interface_id() for interface in self.interfaces if interface.type == InterfaceType.OUTPUT]
        return ServerInterfaceSettings(
            inputs=inputs,
            outputs=outputs,
        )

    def contains(
        self,
        client_interface: ModelInterfaceClient,
    ) -> bool:
        for interface in self.interfaces:
            if client_interface.matches_server_interface(interface):
                return True
        return False

    def output_interfaces(self) -> Tuple[ModelInterfaceServer, ...]:
        return tuple(interface for interface in self.interfaces if interface.type == InterfaceType.OUTPUT)

    def output_interfaces_model_interface_ids(self) -> Tuple[ModelInterfaceId, ...]:
        return tuple(interface.model_interface_id for interface in self.output_interfaces())

    def input_interfaces(self) -> Tuple[ModelInterfaceServer, ...]:
        return tuple(interface for interface in self.interfaces if interface.type == InterfaceType.INPUT)

    def input_interfaces_model_interface_ids(self) -> Tuple[ModelInterfaceId, ...]:
        return tuple(interface.model_interface_id for interface in self.input_interfaces())


class LogicalDelay:

    @staticmethod
    def of_config(
            logical_delay_block_raw_json: dict[str, Any],
            logical_delay_index: int,
            clients: List[ClientSimulatorConfig],
    ) -> LogicalDelay:
        return LogicalDelay(
            delayed_time_steps=int(logical_delay_block_raw_json["delay"]),
            logical_delay_connections=[
                LogicalDelayConnection.of_config(
                    logical_delay_interface, clients,
                    logical_delay_index,
                ) for
                logical_delay_interface in
                logical_delay_block_raw_json["output_connections"]
            ],
        )

    def __init__(
        self,
        delayed_time_steps: int,
        logical_delay_connections: List[LogicalDelayConnection],
    ):
        self.delayed_time_steps: int = delayed_time_steps
        self.logical_delay_connections: List[LogicalDelayConnection] = logical_delay_connections

    def __str__(self) -> str:
        return f"LogicalDelay(delayed_time_step: {self.delayed_time_steps}, connections: [{self.logical_delay_connections}])"

    def __repr__(self) -> str:
        return self.__str__()


class LogicalDelayConnection:

    @staticmethod
    def of_config(
            delay_raw_json: dict[str, Any],
            clients: List[ClientSimulatorConfig],
            logical_delay_index: int,
    ) -> LogicalDelayConnection:
        output_interface = LogicalDelayConnection._find_output_interface(delay_raw_json, clients)
        return LogicalDelayConnection(
            start_value=float(delay_raw_json["start_value"]),
            input_interface=LogicalDelayConnection._find_input_interface_for(
                output_interface,
                clients,
                logical_delay_index,
            ),
            output_interface=output_interface,
        )

    @staticmethod
    def _find_input_interface_for(
            output_simulator_interface_id: SimulatorInterfaceId,
            clients: List[ClientSimulatorConfig],
            logical_delay_index: int,
    ) -> SimulatorInterfaceId:
        output_interface = LogicalDelayConnection.server_model_interface_by_simulator_interface_id(
            clients=clients,
            simulator_interface_id=output_simulator_interface_id,
        )
        if not output_interface:
            raise RuntimeError(
                f"{output_simulator_interface_id} was not found in simulation config",
            )
        input_interface_id: SimulatorInterfaceId | None = None

        for client in clients:
            matching_interfaces = [
                connected_to_data.simulator_interface_id for client_interface in client.interfaces if
                output_simulator_interface_id == client_interface.simulator_interface_id for
                connected_to_data in
                client_interface.connected_to if
                str(logical_delay_index + 1) in connected_to_data.delay_path
            ]
            if len(matching_interfaces) == 1:
                input_interface_id = matching_interfaces[0]
            elif len(matching_interfaces) >= 1:
                SimulationConfig.logger.error(
                    f"There are multiple matching input interfaces for {output_simulator_interface_id} but there must only be one. " +
                    "The first one is used but you need to investigate this issue.",
                )
                input_interface_id = matching_interfaces[0]
        if input_interface_id:
            return input_interface_id
        else:
            raise RuntimeError(f"No input interface for {output_simulator_interface_id} found.")

    @staticmethod
    def server_model_interface_by_simulator_interface_id(
            clients: List[ClientSimulatorConfig],
            simulator_interface_id: SimulatorInterfaceId,
    ) -> ModelInterfaceServer | None:
        client = next(
            (
                client for client in clients if
                client.simulator_name == simulator_interface_id.simulator_name and
                client.model_name == simulator_interface_id.model_interface_id.model_name
            ),
            None,
        )
        if client is None:
            SimulationConfig.logger.warning(
                f"Querying the simulation config for simulator interface id '{simulator_interface_id}' was not successful -> " +
                "no clients match the criteria",
            )
            return None
        for interface in client.interfaces:
            if interface.simulator_interface_id == simulator_interface_id:
                return interface
        SimulationConfig.logger.warning(
            f"Querying the simulation config for simulator interface id '{simulator_interface_id}' was not successful -> client was found " +
            f"({client.client_id}) but does not contain a matching interface",
        )
        return None

    @staticmethod
    def _find_output_interface(
            delay_raw_json: dict[str, Any],
            clients: List[ClientSimulatorConfig],
    ) -> SimulatorInterfaceId:
        output_simulator_name: str = delay_raw_json["destination_simulator_name"]
        for client in clients:
            if client.simulator_name == output_simulator_name:
                return SimulatorInterfaceId(
                    simulator_name=output_simulator_name,
                    model_interface_id=ModelInterfaceId(
                        model_name=client.model_name,
                        interface=delay_raw_json["destination_interface_name"],
                    ),
                )
        raise RuntimeError(
            f"Cannot parse {delay_raw_json} since there is no simulator '{output_simulator_name}' in the client configs",
        )

    def __init__(
        self,
        start_value: float,
        input_interface: SimulatorInterfaceId,
        output_interface: SimulatorInterfaceId,
    ):
        self.start_value = start_value
        self.current_value = start_value
        self.input_interface = input_interface
        self.output_interface = output_interface

    def __str__(self) -> str:
        return (f"LogicalDelayConnection(start_value={self.start_value}, input_interface='{self.input_interface}', " +
                f"output_interface='{self.output_interface}')")

    def __repr__(self) -> str:
        return self.__str__()
