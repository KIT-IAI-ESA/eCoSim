from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, asdict
from typing import TypeVar, Type, Dict, Any


@dataclass(frozen=True)
class MessageData(ABC):
    @classmethod
    def of_json(
        cls: Type[MESSAGE_DATA],
        value: Dict[str, Any],
    ) -> MESSAGE_DATA:
        # noinspection PyArgumentList
        return cls(**value)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


MESSAGE_DATA = TypeVar("MESSAGE_DATA", bound=MessageData)
