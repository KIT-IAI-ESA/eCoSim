from dataclasses import dataclass, field


@dataclass
class ManualClock:
    """Replaces time.monotonic in a test."""

    now: float = field(default=0.0)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds
