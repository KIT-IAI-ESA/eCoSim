from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from ecosim_common.communication.communication_protocol import CommunicationProtocol


@dataclass(frozen=True)
class PerformanceResult:
    test_name: str
    start_time_in_seconds: float | None
    execution_time_in_seconds: float | None
    stop_time_in_seconds: float | None
    server_uptime_in_seconds: float | None
    total_time_in_seconds: float
    tags: List[str]
    communication_protocol: CommunicationProtocol
    date: datetime
    machine: str
