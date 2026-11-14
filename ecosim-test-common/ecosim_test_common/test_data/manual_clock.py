from dataclasses import dataclass, field


@dataclass
class ManualClock:
    """Stands in for time.monotonic: the time moves only when a test moves it."""

    now: float = field(default=0.0)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds
