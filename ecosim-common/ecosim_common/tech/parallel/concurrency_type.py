from enum import Enum


class ConcurrencyType(Enum):
    DASK = "dask"
    THREAD = "thread"
