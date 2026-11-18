class Room:
    def __init__(self) -> None:
        self.temperature = 20.0

    def initialize(self) -> dict[str, float]:
        return {"temperature": self.temperature}

    def do_step(self, inputs: dict[str, float], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        self.temperature += 0.001 * inputs["heating_power"] * step_size_in_seconds
        return {"temperature": self.temperature}

    def clear(self) -> None:
        pass
