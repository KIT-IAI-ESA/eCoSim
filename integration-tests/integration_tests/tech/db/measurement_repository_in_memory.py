from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Tuple, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.tech.structures.esp_map import ESPMap, ThreadESPMap
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository import MeasurementRepository


@dataclass(frozen=True)
class MeasurementRepositoryInMemory(MeasurementRepository):
    _records: ESPMap[datetime, Tuple[ProtocolInterfaceValue, ...]] = field(default_factory=lambda: ThreadESPMap())

    @staticmethod
    def for_protocol(protocol: CommunicationProtocol) -> MeasurementRepositoryInMemory:
        return MeasurementRepositoryInMemory(_records=ThreadESPMap())

    @override
    def add(
        self,
        values: Tuple[ProtocolInterfaceValue, ...],
        timestamp: datetime,
    ) -> None:
        self._records[timestamp] = values

    @override
    def all(self) -> List[MeasurementEntry]:
        return [
            MeasurementEntry(
                timestamp=timestamp,
                values=values,
            )
            for timestamp, values in self._records.items()
        ]

    def assert_entry_count(
        self,
        entry_count: int,
    ) -> MeasurementRepositoryInMemory:
        assert len(self._records) == entry_count, f"Expected {entry_count} entries, got {len(self._records)}"
        return self

    def assert_for_each_record(
        self,
        assertion: Callable[[datetime, Tuple[ProtocolInterfaceValue, ...]], bool],
    ) -> MeasurementRepositoryInMemory:
        for timestamp, values in self._records.items():
            assert assertion(timestamp, values)
        return self
