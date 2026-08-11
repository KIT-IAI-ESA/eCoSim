from __future__ import annotations

import pickle
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import MISSING
from typing import Any, Generator, Generic, ItemsView, KeysView, MutableMapping, TypeVar, ValuesView, assert_never, cast, overload, override

from distributed import Actor, Client, Variable, fire_and_forget, get_client
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.logger.with_silenced_logger import silenced_logger
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

K = TypeVar("K")
V = TypeVar("V")

_logger = ESPLogger("ESPMap")


class ESPMap(ABC, MutableMapping[K, V], Generic[K, V]):
    """
    A wrapper around different kind of maps.

    ATTENTION: you need to use 'transaction' if you want to manipulate nested types like objects, lists or other maps.
               E.g. do something like this
               ```
               with esp_map.transaction() as data:
                   data[client_id].interface_data.append(
                       CurrentStepClientDataInterface(
                           interface_value=ProtocolInterfaceValueMutable(name=interface.name, value=None),
                       )
                   )
               ```
               If you try to manipulate those types directly, you only manipulate a local copy, so this will not work.

               You get weird side effects if you manipulate nested types directly, depending on the concrete implementation. So you cannot assume
               that all implementations will behave the same. Therefore, it is strictly not recommended to manipulate nested types directly.
    """

    logger = ESPLogger("ESPMap")

    @staticmethod
    def of_type(
        map_type: ESPStructureType,
        data: dict[K, V] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose: bool = False,
    ) -> ESPMap[K, V]:
        match map_type:
            case ESPStructureType.SIMPLE:
                return SimpleESPMap(
                    data=data,
                    ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose=(
                        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose
                    ),
                )
            case ESPStructureType.DASK_VARIABLE:
                return DaskVariableESPMap(
                    data=data,
                    dask_name=dask_name,
                    dask_client=dask_client,
                )
            # case ESPStructureType.DASK_ACTOR:
            #     return DaskActorESPMap(
            #         data=data,
            #         dask_client=dask_client,
            #     )
            case ESPStructureType.THREAD:
                return ThreadESPMap(
                    data=data,
                )
            case _:
                assert_never(map_type)

    @abstractmethod
    @contextmanager
    def transaction(self) -> Generator[dict[K, V], Any, None]:
        pass

    @abstractmethod
    def get_snapshot(self) -> dict[K, V]:
        pass

    def __getitem__(self, k: K) -> V:
        return self.get_snapshot()[k]

    def __setitem__(self, k: K, v: V) -> None:
        with self.transaction() as internal_map:
            internal_map[k] = v

    def __delitem__(self, k: K) -> None:
        with self.transaction() as internal_map:
            del internal_map[k]

    def __iter__(self) -> Iterator[K]:
        return iter(self.get_snapshot())

    def __len__(self) -> int:
        return len(self.get_snapshot())

    @override
    def clear(self) -> None:
        with self.transaction() as internal_map:
            internal_map.clear()

    @overload  # type: ignore[override]
    def pop(self, k: K) -> V: ...

    @overload
    def pop(self, k: K, v: V) -> V: ...

    @override
    def pop(self, k: K, v: V | object = MISSING) -> V:
        with self.transaction() as internal_map:
            if v is MISSING:
                return internal_map.pop(k)
            return internal_map.pop(k, v)  # type: ignore[return-value]

    @override
    def values(self) -> ValuesView[V]:
        return self.get_snapshot().values()

    @override
    def items(self) -> ItemsView[K, V]:
        return self.get_snapshot().items()

    @override
    def keys(self) -> KeysView[K]:
        return self.get_snapshot().keys()


class SimpleESPMap(ESPMap[K, V]):
    _internal_map: dict[K, V]

    def __init__(
        self,
        data: dict[K, V] | None = None,
        ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose: bool = False,
    ) -> None:
        self._internal_map = dict(data or {})
        self._ignore_thread_safety_logs = ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose

    @override
    def get_snapshot(self) -> dict[K, V]:
        return self._internal_map.copy()

    @contextmanager
    @override
    def transaction(self) -> Generator[dict[K, V], Any, None]:
        if not self._ignore_thread_safety_logs:
            _logger.error(
                "'transaction' is not thread safe for SimpleESPMap -> no lock is used and you will get unpredicted race conditions "
                "-> use ThreadESPMap instead.",
            )
        current = self.get_snapshot()
        yield current
        self._internal_map = current

    def _overwrite_internal(self, overwrite: dict[K, V]) -> None:
        self._internal_map = overwrite


class DaskVariableESPMap(ESPMap[K, V]):
    def __init__(
        self,
        data: dict[K, V] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
    ) -> None:
        init_data = dict(data or {})
        self._dask_variable = Variable(
            client=dask_client,
            name=dask_name or f"esp_map_{uuid.uuid4()}",
        )
        self._lock = ParallelLock.dask(f"espmap_lock_{self._dask_variable.name}")
        with self._lock:
            try:
                # for the case that the variable is already initialized, check if it can be got
                with silenced_logger("distributed.core"):
                    self._dask_variable.get(timeout=0.1)
            except TimeoutError:
                # if it does not exist, initialize it
                self._dask_variable.set(pickle.dumps(init_data))
            except Exception as e:
                ESPMap.logger.warning("Failed to initialize Dask variable, with other than TimeoutError: %s", e)
                self._dask_variable.set(pickle.dumps(init_data))

    @override
    def get_snapshot(self) -> dict[K, V]:
        raw = self._dask_variable.get()
        return pickle.loads(raw)

    @contextmanager
    @override
    def transaction(self) -> Generator[dict[K, V], Any, None]:
        with self._lock:
            current_map = self.get_snapshot()
            yield current_map
            self._dask_variable.set(pickle.dumps(current_map))


class ThreadESPMap(ESPMap[K, V]):
    _internal_map: dict[K, V]

    def __init__(
        self,
        data: dict[K, V] | None = None,
    ) -> None:
        self._internal_map = dict(data or {})
        self._lock = ParallelLock.thread()

    @override
    def get_snapshot(self) -> dict[K, V]:
        return self._internal_map.copy()

    @contextmanager
    @override
    def transaction(self) -> Generator[dict[K, V], Any, None]:
        with self._lock:
            current = self.get_snapshot()
            yield current
            self._internal_map = current


class DaskActorESPMap(ESPMap[K, V]):
    def __init__(
        self,
        data: dict[K, V] | None = None,
        dask_client: Client | None = None,
    ) -> None:
        dask_client = dask_client or get_client()
        self._future = dask_client.submit(
            SimpleESPMap,
            data=data,
            ignore_thread_safety_logs_regarding_transactions_and_yes_this_name_is_extra_long_on_purpose=True,
            actors=True,
        )
        # submitted with 'actors=True', so the result is an Actor proxy and not a SimpleESPMap - every call on it
        # returns an ActorFuture instead of the value itself
        self._actor: Actor = cast(Actor, self._future.result())
        # An actor only lives as long as some client holds a reference to its future.
        # Without pinning the future, the last dropped copy destroys
        # the actor and every further call fails with 'KeyError: SimpleESPMap-<uuid>' on the worker.
        fire_and_forget(self._future)
        self._lock = ParallelLock.dask(f"espmap_lock_{self._actor.key}")

    @override
    def get_snapshot(self) -> dict[K, V]:
        return self._actor.get_snapshot().result()

    @contextmanager
    @override
    def transaction(self) -> Generator[dict[K, V], Any, None]:
        with self._lock:
            current = self.get_snapshot()
            yield current
            # Actor calls are asynchronous: without waiting for the result, the write can land after the lock was
            # released again, which silently loses updates.
            self._actor._overwrite_internal(current).result()  # noqa: SLF001
