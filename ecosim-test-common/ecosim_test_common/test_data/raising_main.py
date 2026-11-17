from dataclasses import dataclass
from typing import Sequence


@dataclass
class RaisingMain:
    error: BaseException
    passed_arguments: Sequence[str] | None = None

    def __call__(self, passed_arguments: Sequence[str]) -> None:
        self.passed_arguments = passed_arguments
        raise self.error
