from datetime import datetime, timedelta
from typing import Callable

from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue, ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.message_type import MessageType


def create_step_batch_message(
    input_interface_names: set[str],
    start_date: datetime,
    number_of_steps: int,
    step_size: float,
    input_value_generator: Callable[[str, float], InterfaceValue],
) -> ESPChannelMessageJson:
    inputs = {
        start_date + timedelta(seconds=seconds): [
            ProtocolInterfaceValue(name=name, value=input_value_generator(name, seconds)) for name in input_interface_names
        ]
        # the keys are the end times of the steps, so the first one is one step after 'start_date'
        for seconds in (step * step_size for step in range(1, number_of_steps + 1))
    }
    batch = SimulationStepBatchRequest(start_datetime=start_date, inputs=inputs)
    return ESPChannelMessageJson.create(type=MessageType.SIMULATION_STEP_BATCH, payload=batch)
