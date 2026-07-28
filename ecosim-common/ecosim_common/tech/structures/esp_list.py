from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, MutableSequence
from contextlib import contextmanager
from typing import Any, Generator, Generic, TypeVar, assert_never, overload, override

# TODO_SECURITY: cloudpickle also pickles lambdas -> in a bigger co-simulation with external partners, this might be a security issue
import cloudpickle
from distributed import Client, Variable
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.logger.with_silenced_logger import silenced_logger
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

T = TypeVar("T")

_logger = ESPLogger("ESPList")


class ESPList(ABC, MutableSequence[T], Generic[T]):
    """
    A wrapper around different kind of lists.

    ATTENTION: you need to use 'transaction' if you want to mutate the list (append/insert/remove/etc.).
               E.g. do something like this
               ```
               with esp_list.transaction() as data:
                   data.append(client_id)
                   data.remove(old_client_id)
               ```
               If you try to mutate directly, you only mutate a local copy, so this will not work.

               You get weird side effects if you mutate directly, depending on the concrete implementation. So you cannot assume
               that all implementations will behave the same. Therefore, it is strictly not recommended to mutate directly.
    """

    @staticmethod
    def of_type(
        list_type: ESPStructureType,
        data: list[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        dask_use_pickle: bool = True,
        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose: bool = False,
    ) -> ESPList[T]:
        match list_type:
            case ESPStructureType.SIMPLE:
                return SimpleESPList(
                    data=data,
                    ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose=(
                        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose
                    ),
                )
            case ESPStructureType.DASK_VARIABLE:
                return DaskESPList(
                    data=data,
                    dask_name=dask_name,
                    dask_client=dask_client,
                    use_pickle=dask_use_pickle,
                )
            case ESPStructureType.THREAD:
                return ThreadESPList(
                    data=data,
                )
            case _:
                assert_never(list_type)

    @abstractmethod
    @contextmanager
    def transaction(self) -> Generator[list[T], Any, None]:
        pass

    @abstractmethod
    def get_snapshot(self) -> list[T]:
        pass

    def __contains__(self, x: object) -> bool:
        return x in self.get_snapshot()

    def __iter__(self) -> Iterator[T]:
        return iter(self.get_snapshot())

    def __len__(self) -> int:
        return len(self.get_snapshot())

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index: int | slice) -> T | list[T]:
        return self.get_snapshot()[index]

    @overload
    def __setitem__(self, index: int, value: T) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[T]) -> None: ...

    def __setitem__(self, index: int | slice, value: Any) -> None:
        with self.transaction() as internal_list:
            internal_list[index] = value

    def __delitem__(self, index: int | slice) -> None:
        with self.transaction() as internal_list:
            del internal_list[index]

    def insert(self, index: int, value: T) -> None:
        with self.transaction() as internal_list:
            internal_list.insert(index, value)

    def append(self, value: T) -> None:
        with self.transaction() as internal_list:
            internal_list.append(value)

    def extend(self, values: Iterable[T]) -> None:
        with self.transaction() as internal_list:
            internal_list.extend(values)

    def remove(self, value: T) -> None:
        with self.transaction() as internal_list:
            internal_list.remove(value)

    def pop(self, index: int = -1) -> T:
        with self.transaction() as internal_list:
            return internal_list.pop(index)

    def clear(self) -> None:
        with self.transaction() as internal_list:
            internal_list.clear()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ESPList):
            return self.get_snapshot() == other.get_snapshot()
        if isinstance(other, list):
            return self.get_snapshot() == other
        return NotImplemented


class SimpleESPList(ESPList[T]):
    _internal_list: list[T]

    def __init__(
        self,
        data: list[T] | None = None,
        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose: bool = False,
    ) -> None:
        self._internal_list = list(data or [])
        self._ignore_thread_safety_logs = ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose

    @override
    def get_snapshot(self) -> list[T]:
        return self._internal_list.copy()

    @contextmanager
    @override
    def transaction(self) -> Generator[list[T], Any, None]:
        if not self._ignore_thread_safety_logs:
            _logger.error(
                "'transaction' is not thread safe for SimpleESPList -> no lock is used and you will get unpredicted race conditions "
                + "-> use ThreadESPList instead.",
            )
        current = self.get_snapshot()
        yield current
        self._internal_list = current


class DaskESPList(ESPList[T]):
    def __init__(
        self,
        data: list[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        use_pickle: bool = False,
    ) -> None:
        init_data = list(data or [])
        self._dask_variable = Variable(
            client=dask_client,
            name=dask_name or f"esp_list_{uuid.uuid4()}",
        )
        self._use_pickle = use_pickle
        self._lock = ParallelLock.dask(f"lock_{self._dask_variable.name}")
        try:
            # for the case that the variable is already initialized, check if it can be got
            with silenced_logger("distributed.core"):
                self._dask_variable.get(timeout=0.1)
        except Exception:
            # if it does not exist, initialize it
            self._dask_variable.set(self._serialize(init_data))

    def _serialize(self, data: list[T]) -> Any:
        if self._use_pickle:
            return cloudpickle.dumps(data)
        return data

    def _deserialize(self, data: Any) -> list[T]:
        if self._use_pickle:
            return cloudpickle.loads(data)
        return list(data)

    @override
    def get_snapshot(self) -> list[T]:
        raw = self._dask_variable.get()
        return self._deserialize(raw)

    @contextmanager
    @override
    def transaction(self) -> Generator[list[T], Any, None]:
        with self._lock:
            current_list = self.get_snapshot()
            yield current_list
            self._dask_variable.set(self._serialize(current_list))


class ThreadESPList(ESPList[T]):
    _internal_list: list[T]

    def __init__(
        self,
        data: list[T] | None = None,
    ) -> None:
        self._internal_list = list(data or [])
        self._lock = ParallelLock.thread()

    @override
    def get_snapshot(self) -> list[T]:
        return self._internal_list.copy()

    @contextmanager
    @override
    def transaction(self) -> Generator[list[T], Any, None]:
        with self._lock:
            current = self.get_snapshot()
            yield current
            self._internal_list = current
