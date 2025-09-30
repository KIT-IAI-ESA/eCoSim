from dataclasses import dataclass

from ecosim_common.communication.channel.message_data import MessageData


@dataclass(frozen=True)
class SimulationSetupMessage(MessageData):
    step_size_in_ms: int
