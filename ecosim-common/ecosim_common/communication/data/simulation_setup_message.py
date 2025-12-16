from dataclasses import dataclass

from ecosim_common.communication.channel.message_data import MessageData


@dataclass(frozen=True)
class SimulationSetupMessage(MessageData):
    step_size_in_ms: int
    step_size_in_us: int | None = None

    @property
    def step_size_in_microseconds(self) -> int:
        """Returns step size in microseconds, converting from milliseconds if needed."""
        if self.step_size_in_us is not None:
            return self.step_size_in_us
        return self.step_size_in_ms * 1000
