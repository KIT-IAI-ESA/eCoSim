from dataclasses import dataclass
from typing import Sequence


@dataclass
class RaisingMain:
    """The main of a console script that stops with an error."""

    error: BaseException
    passed_arguments: Sequence[str] | None = None

    def __call__(self, passed_arguments: Sequence[str]) -> None:
        self.passed_arguments = passed_arguments
        raise self.error
