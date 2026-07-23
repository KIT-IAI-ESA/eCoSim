from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, assert_never

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType, ProtocolInterfaceValue, ProtocolInterfaceValueMutable
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ConnectedToData
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_int import ESPInt
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig


# TODO_AFTER_MERGE: make usuable for both normal and HPC/dask
class CurrentStepData:
    _logger = ESPLogger("CurrentStepData")

    def __init__(
        self,
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
    ):
        self._step: ESPInt
        self._simulation_config: SimulationConfig = simulation_config
        self._data_by_client: ESPMap[ClientID, CurrentStepClientData]
        self._logical_delays: ESPMap[int, CurrentStepLogicalDelay]
        match server_config.server.communication_protocol:
            case CommunicationProtocol.DASK:
                self._step = ESPInt.of_type(ESPStructureType.DASK, value=0)
                self._data_by_client = ESPMap.of_type(ESPStructureType.DASK)
                self._logical_delays = ESPMap.of_type(ESPStructureType.DASK)
            case CommunicationProtocol.TCP_SOCKET:
                self._step = ESPInt.of_type(ESPStructureType.SIMPLE, value=0)
                self._data_by_client = ESPMap.of_type(
                    ESPStructureType.SIMPLE,
                    ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose=True,
                )
                self._logical_delays = ESPMap.of_type(
                    ESPStructureType.SIMPLE,
                    ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose=True,
                )
            case _:
                assert_never(server_config.server.communication_protocol)
        self._init_logical_delays()

    def reset_for_new_step(
        self,
        step: int,
    ) -> None:
        self._step.set(step)
        self._reset_interfaces_by_client()

    def _init_logical_delays(self) -> None:
        for logical_delay in self._simulation_config.logical_delays:
            delayed_time_steps = logical_delay.delayed_time_steps
            if delayed_time_steps not in self._logical_delays:
                with self._logical_delays.transaction() as logical_delays:
                    logical_delays[delayed_time_steps] = CurrentStepLogicalDelay(
                        delayed_time_steps=delayed_time_steps,
                        connections=[],
                    )
            for logical_delay_connection in logical_delay.logical_delay_connections:
                with self._logical_delays.transaction() as logical_delays:
                    logical_delays[delayed_time_steps].connections.append(
                        CurrentStepLogicalDelayConnection(
                            current_value=logical_delay_connection.start_value,
                            output_interface=logical_delay_connection.output_interface,
                            input_interface=logical_delay_connection.input_interface,
                            set_in_step=[],
                        ),
                    )

    def _reset_interfaces_by_client(self) -> None:
        self._data_by_client.clear()
        for client in self._simulation_config.clients:
            with self._data_by_client.transaction() as data_by_client:
                data_by_client[client.client_id] = CurrentStepClientData(executed=False, interface_data=[])
            for interface in client.interfaces:
                if interface.type == InterfaceType.OUTPUT:
                    continue
                with self._data_by_client.transaction() as data_by_client:
                    data_by_client[client.client_id].interface_data.append(
                        CurrentStepClientDataInterface(
                            interface_value=ProtocolInterfaceValueMutable(name=interface.name, value=None),
                            connected_to=tuple(interface.connected_to),
                        ),
                    )

    def set_value(
        self,
        interface: SimulatorInterfaceId,
        value: InterfaceValueType,
    ) -> None:
        with self._data_by_client.transaction() as data_by_client:
            client_data = data_by_client[interface.client_id()]
            if client_data.executed:
                CurrentStepData._logger.error(
                    f"(CurrentStep: {self._step.get()}): Setting value for execution for interface {interface} but it is already executed",
                )
                return
            for interface_data in client_data.interface_data:
                if interface_data.interface_value.name == interface.model_interface_id.interface:
                    if interface_data.interface_value.value is not None:
                        CurrentStepData._logger.warning(
                            f"(CurrentStep: {self._step.get()})Setting value for execution for interface {interface} but it is already set => "
                            + f"overwriting old value of {interface_data.interface_value.value} with {value}",
                        )
                        return
                    interface_data.interface_value.value = value
                    return
        CurrentStepData._logger.error(
            f"(CurrentStep: {self._step.get()}) Could not find {interface} to set execution value to {value}",
        )

    def get_ready_for_execution(self) -> dict[ClientID, List[ProtocolInterfaceValue]]:
        result: dict[ClientID, List[ProtocolInterfaceValue]] = {}
        for client_id in self._data_by_client:
            client_data: CurrentStepClientData = self._data_by_client[client_id]
            if client_data.executed or any(interface_data_entry.interface_value.value is None for interface_data_entry in client_data.interface_data):
                continue
            result[client_id] = [interface_data_entry.interface_value.to_immutable() for interface_data_entry in client_data.interface_data]
        return result

    def add_received_data(
        self,
        client_id_sender: ClientID,
        interface_values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        CurrentStepData._logger.debug(f"CurrentStepData#add_received_data: entry for {client_id_sender}")
        client_config_sender = self._simulation_config.client_simulator_config_for(client_id_sender)

        if client_config_sender is None:
            CurrentStepData._logger.error(f"CurrentStepData#add_received_data: Cannot find client sender for client {client_id_sender}")
            return

        for interface_value in interface_values:
            simulator_interface_id_sender = SimulatorInterfaceId(
                simulator_name=client_config_sender.simulator_name,
                model_interface_id=ModelInterfaceId(
                    model_name=client_config_sender.model_name,
                    interface=interface_value.name,
                ),
            )
            new_value = interface_value.value
            for client_id_receiver in self._data_by_client.keys():
                if client_id_receiver == client_id_sender:
                    continue
                client_config_receiver = self._simulation_config.client_simulator_config_for(client_id_receiver)
                if client_config_receiver is None:
                    CurrentStepData._logger.error(f"CurrentStepData#add_received_data: Cannot find client receiver for client {client_id_receiver}")
                    return
                for interface_data_entry in self._data_by_client[client_id_receiver].interface_data:
                    if interface_data_entry.settable_by(simulator_interface_id_sender):
                        self.set_value(
                            SimulatorInterfaceId(
                                simulator_name=client_config_receiver.simulator_name,
                                model_interface_id=ModelInterfaceId(
                                    model_name=client_config_receiver.model_name,
                                    interface=interface_data_entry.interface_value.name,
                                ),
                            ),
                            new_value,
                        )

            with self._logical_delays.transaction() as logical_delays:
                for logical_delay in logical_delays.values():
                    for logical_delay_connection in logical_delay.connections:
                        if logical_delay_connection.settable_by(simulator_interface_id_sender):
                            if self._step.get() in logical_delay_connection.set_in_step:
                                CurrentStepData._logger.warning(
                                    f"Connection {logical_delay_connection.input_interface} in logical delay {logical_delay.delayed_time_steps} was "
                                    + f"already set in time step {self._step.get()}. This should not happen. The current value "
                                    + f"{logical_delay_connection.current_value} will be overwritten with {new_value}.",
                                )
                            logical_delay_connection.current_value = new_value
        CurrentStepData._logger.debug(f"CurrentStepData#add_received_data: exit for {client_id_sender}")

    def all_clients_executed(self) -> bool:
        return all([self._data_by_client[client_id].executed for client_id in self._data_by_client.keys()])

    def set_is_executed(
        self,
        client_id: ClientID,
    ) -> None:
        with self._data_by_client.transaction() as data_by_client:
            data_by_client[client_id].executed = True

    def logical_delays_by_delay_step(self) -> ESPMap[int, CurrentStepLogicalDelay]:
        return self._logical_delays


@dataclass
class CurrentStepClientData:
    executed: bool
    interface_data: List[CurrentStepClientDataInterface]


@dataclass
class CurrentStepClientDataInterface:
    interface_value: ProtocolInterfaceValueMutable
    connected_to: Tuple[ConnectedToData, ...]

    def settable_by(
        self,
        simulator_interface_id: SimulatorInterfaceId,
    ) -> bool:
        return any(
            (matched_interface.simulator_interface_id == simulator_interface_id and len(matched_interface.delay_path) == 0)
            for matched_interface in self.connected_to
        )


@dataclass
class CurrentStepLogicalDelay:
    delayed_time_steps: int
    connections: List[CurrentStepLogicalDelayConnection]


@dataclass
class CurrentStepLogicalDelayConnection:
    current_value: InterfaceValueType
    output_interface: SimulatorInterfaceId
    input_interface: SimulatorInterfaceId
    set_in_step: List[int]

    def settable_by(
        self,
        simulator_interface_id: SimulatorInterfaceId,
    ) -> bool:
        return self.input_interface == simulator_interface_id
