from __future__ import annotations

from enum import Enum


class ESPStructureType(Enum):
    DASK_VARIABLE = "dask_variable"
    # DASK_ACTOR = "dask_actor"
    THREAD = "thread"
    SIMPLE = "simple"
