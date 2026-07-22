from __future__ import annotations

from enum import Enum


class ESPStructureType(Enum):
    DASK = "dask"
    THREAD = "thread"
    SIMPLE = "simple"
