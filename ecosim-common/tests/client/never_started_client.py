from typing import override

from ecosim_common.client.client import Client
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.simulation.interface_id import InterfaceId


class NeverStartedClient(Client):
    @override
    def on_simulation_start(self) -> ClientSimStepData:
        return ClientSimStepData(interface_values=[])

    @override
    def on_simulation_step(
        self,
        received_inputs: dict[InterfaceId, InterfaceValue],
        step_size_in_seconds: float,
    ) -> ClientSimStepData:
        return ClientSimStepData(interface_values=[])

    @override
    def on_simulation_stop(self) -> None:
        pass
