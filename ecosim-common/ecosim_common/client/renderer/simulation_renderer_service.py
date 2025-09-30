from abc import ABC, abstractmethod


class SimulationRendererService(ABC):

    @abstractmethod
    def render_step(self, time_step: int) -> bytes | None:
        pass
