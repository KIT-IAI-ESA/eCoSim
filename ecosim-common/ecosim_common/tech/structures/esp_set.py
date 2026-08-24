from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator, Set
from contextlib import contextmanager
from typing import Any, Generator, Generic, TypeVar, assert_never, override

# TODO_SECURITY: cloudpickle also pickles lambdas -> in a bigger co-simulation with external partners, this might be a security issue
import cloudpickle
from distributed import Client, Variable
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.structures.dask_variable_initializer import DaskVariableInitializer
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

T = TypeVar("T")

_logger = ESPLogger("ESPSet")


class ESPSet(ABC, Set[T], Generic[T]):
    """
    A wrapper around different kind of sets.

    ATTENTION: you need to use 'transaction' if you want to mutate the set (add/remove/discard).
               E.g. do something like this
               ```
               with esp_set.transaction() as data:
                   data.add(client_id)
                   data.discard(old_client_id)
               ```
               If you try to mutate directly, you only mutate a local copy, so this will not work.

               You get weird side effects if you mutate directly, depending on the concrete implementation. So you cannot assume
               that all implementations will behave the same. Therefore, it is strictly not recommended to mutate directly.
    """

    @staticmethod
    def of_type(
        set_type: ESPStructureType,
        data: set[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose: bool = False,
    ) -> ESPSet[T]:
        match set_type:
            case ESPStructureType.SIMPLE:
                return SimpleESPSet(
                    data=data,
                    ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose=(
                        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose
                    ),
                )
            case ESPStructureType.DASK_VARIABLE:
                return DaskESPSet(
                    data=data,
                    dask_name=dask_name,
                    dask_client=dask_client,
                )
            case ESPStructureType.THREAD:
                return ThreadESPSet(
                    data=data,
                )
            case _:
                assert_never(set_type)

    @abstractmethod
    @contextmanager
    def transaction(self) -> Generator[set[T], Any, None]:
        pass

    @abstractmethod
    def get_snapshot(self) -> set[T]:
        pass

    def __contains__(self, x: object) -> bool:
        return x in self.get_snapshot()

    def __iter__(self) -> Iterator[T]:
        return iter(self.get_snapshot())

    def __len__(self) -> int:
        return len(self.get_snapshot())

    def add(self, value: T) -> None:
        with self.transaction() as internal_set:
            internal_set.add(value)

    def discard(self, value: T) -> None:
        with self.transaction() as internal_set:
            internal_set.discard(value)

    def remove(self, value: T) -> None:
        with self.transaction() as internal_set:
            internal_set.remove(value)

    def clear(self) -> None:
        with self.transaction() as internal_set:
            internal_set.clear()


class SimpleESPSet(ESPSet[T]):
    _internal_set: set[T]

    def __init__(
        self,
        data: set[T] | None = None,
        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose: bool = False,
    ) -> None:
        self._internal_set = set(data or set())
        self._ignore_thread_safety_logs = ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose

    @override
    def get_snapshot(self) -> set[T]:
        return self._internal_set.copy()

    @contextmanager
    @override
    def transaction(self) -> Generator[set[T], Any, None]:
        if not self._ignore_thread_safety_logs:
            _logger.error(
                "'transaction' is not thread safe for SimpleESPSet -> no lock is used and you will get unpredicted race conditions "
                "-> use ThreadESPSet instead.",
            )
        current = self.get_snapshot()
        yield current
        self._internal_set = current


class DaskESPSet(ESPSet[T]):
    def __init__(
        self,
        data: set[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
    ) -> None:
        init_data = set(data or set())
        self._dask_variable = Variable(
            client=dask_client,
            name=dask_name or f"esp_set_{uuid.uuid4()}",
        )
        self._lock = ParallelLock.dask()
        DaskVariableInitializer.initialize(
            variable=self._dask_variable,
            value_supplier=lambda: cloudpickle.dumps(init_data),
            may_already_exist=dask_name is not None,
        )

    @override
    def get_snapshot(self) -> set[T]:
        raw = self._dask_variable.get()
        return cloudpickle.loads(raw)

    @contextmanager
    @override
    def transaction(self) -> Generator[set[T], Any, None]:
        with self._lock:
            current_set = self.get_snapshot()
            yield current_set
            self._dask_variable.set(cloudpickle.dumps(current_set))


class ThreadESPSet(ESPSet[T]):
    _internal_set: set[T]

    def __init__(
        self,
        data: set[T] | None = None,
    ) -> None:
        self._internal_set = set(data or set())
        self._lock = ParallelLock.thread()

    @override
    def get_snapshot(self) -> set[T]:
        return self._internal_set.copy()

    @contextmanager
    @override
    def transaction(self) -> Generator[set[T], Any, None]:
        with self._lock:
            current = self.get_snapshot()
            yield current
            self._internal_set = current
