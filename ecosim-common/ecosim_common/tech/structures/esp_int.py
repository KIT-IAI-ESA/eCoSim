from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cache
from typing import Callable, assert_never, override

from distributed import Variable
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.structures.dask_variable_initializer import DaskVariableInitializer
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


class ESPInt(ABC):
    @staticmethod
    def of_type(
        structure_type: ESPStructureType,
        value: int = 0,
        dask_name: str | None = None,
    ) -> ESPInt:
        match structure_type:
            case ESPStructureType.SIMPLE:
                return SimpleESPInt(_value=value)
            case ESPStructureType.DASK_VARIABLE:
                return DaskESPInt(value=value, dask_name=dask_name)
            case ESPStructureType.THREAD:
                return ThreadESPInt(value=value)
            case _:
                assert_never(structure_type)

    @abstractmethod
    def get(self) -> int:
        pass

    @abstractmethod
    def set(self, v: int) -> None:
        pass

    @abstractmethod
    def increment(self, by: int = 1) -> int:
        pass

    def get_temporary_cache(self) -> Callable[[], int]:
        @cache
        def cached_int() -> int:
            return self.get()

        return cached_int


@dataclass
class SimpleESPInt(ESPInt):
    _value: int = field()

    @override
    def get(self) -> int:
        return self._value

    @override
    def set(self, v: int) -> None:
        self._value = v

    @override
    def increment(self, by: int = 1) -> int:
        self._value += by
        return self._value


class DaskESPInt(ESPInt):
    def __init__(
        self,
        value: int = 0,
        dask_name: str | None = None,
    ) -> None:
        self._dask_variable: Variable = Variable(name=dask_name)
        self._lock = ParallelLock.dask(f"int_lock_{dask_name or uuid.uuid4()}")
        DaskVariableInitializer.initialize(
            variable=self._dask_variable,
            value_supplier=lambda: value,
            may_already_exist=dask_name is not None,
        )

    @override
    def get(self) -> int:
        return self._dask_variable.get()

    @override
    def set(self, v: int) -> None:
        with self._lock:
            self._dask_variable.set(v)

    @override
    def increment(self, by: int = 1) -> int:
        with self._lock:
            new_value = self._dask_variable.get() + by
            self._dask_variable.set(new_value)
        return new_value


class ThreadESPInt(ESPInt):
    def __init__(
        self,
        value: int = 0,
    ) -> None:
        self._value = value
        self._lock = threading.Lock()

    @override
    def get(self) -> int:
        return self._value

    @override
    def set(self, v: int) -> None:
        with self._lock:
            self._value = v

    @override
    def increment(self, by: int = 1) -> int:
        with self._lock:
            self._value = self._value + by
            return self._value
