from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set, Tuple

from ecosim_common.tech.json.dataclass_json_converter import DataclassJsonConverter

TIMESTAMP = datetime.datetime(2026, 8, 26, 10, 0, 0, tzinfo=datetime.timezone.utc)


class Quality(Enum):
    GOOD = "good"
    BAD = "bad"


@dataclass(frozen=True)
class Reading:
    name: str
    value: float

    def test_method(self) -> str:
        return self.name


@dataclass
class Entry:
    timestamp: datetime.datetime
    readings: Tuple[Reading, ...]
    quality: Quality
    tags: List[str]
    lookup: Dict[str, float]

    def test_method(self) -> Quality:
        return self.quality


@dataclass
class FlatEntry:
    name: str
    value: float
    comment: str | None = None


@dataclass
class SetEntry:
    values: Set[str]


@dataclass
class OptionalEntry:
    timestamp: datetime.datetime | None = None


def create_entry() -> Entry:
    return Entry(
        timestamp=TIMESTAMP,
        readings=(Reading(name="room_temperature", value=293.15),),
        quality=Quality.GOOD,
        tags=["house", "heating"],
        lookup={"delta_t": 60.0},
    )


def to_json_string_then_json_loads(data: Any) -> dict[str, Any]:
    return json.loads(DataclassJsonConverter.to_json_string(data))


def round_tripped_to_and_of_json_string(entry_type: type, data: Any) -> Any:
    return DataclassJsonConverter.of_json_string(entry_type, DataclassJsonConverter.to_json_string(data))
