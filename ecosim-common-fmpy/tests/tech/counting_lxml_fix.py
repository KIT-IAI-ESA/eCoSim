from dataclasses import dataclass, field
from time import sleep


@dataclass
class CountingLxmlFix:
    delay_in_seconds: float = field(default=0.0)
    call_count: int = field(default=0)

    def __call__(self) -> None:
        sleep(self.delay_in_seconds)
        self.call_count += 1
