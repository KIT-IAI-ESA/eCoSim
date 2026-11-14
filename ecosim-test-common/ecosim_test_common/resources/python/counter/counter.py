class Counter:
    """Counts its steps, so the stored values show that every step reached the model."""

    def __init__(self) -> None:
        self.steps = 0

    def initialize(self) -> dict[str, float]:
        return {"count": 0.0}

    def do_step(self, inputs: dict[str, float], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        self.steps += 1
        return {"count": float(self.steps)}

    def clear(self) -> None:
        pass
