from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import TypeVar, cast

from dask.distributed import Client, Lock, Variable
from ecosim_common.tech.logger.with_silenced_logger import silenced_logger

KT = TypeVar("KT")
VT = TypeVar("VT")
RT = TypeVar("RT")


@dataclass(eq=False, repr=False)
class DaskDictionaryForSimpleTypes(MutableMapping[KT, VT]):
    """
    Scheduler-backed dict shared across Dask clients. Every read is a round-trip.

    ATTENTION: This will only work for simple types.

    E.g.:
       my_dict[key].value_1 = 22
       my_dict[key].value_2 = 33

    will not propagate to other clients.
    """

    name: str
    client: Client | None = None
    default: Mapping[KT, VT] | None = None

    _dask_variable: Variable = field(init=False, repr=False, compare=False)
    _dask_lock: Lock = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._dask_variable = Variable(
            name=self.name,
            client=self.client,
        )
        self._dask_lock = Lock(
            name=f"{self.name}-lock",
        )
        with self._dask_lock:
            try:
                # in case that the variable is already initialized, check if it can be got
                with silenced_logger("distributed.core"):
                    self._dask_variable.get(timeout="1s")
            except TimeoutError:
                self._dask_variable.set(dict(self.default or {}))

    def _fetch(self) -> dict[KT, VT]:
        return cast("dict[KT, VT]", self._dask_variable.get())

    def _mutate(self, fn: Callable[[dict[KT, VT]], RT]) -> RT:
        with self._dask_lock:
            d = dict(self._fetch())
            out = fn(d)
            self._dask_variable.set(d)
        return out

    def __getitem__(self, key: KT) -> VT:
        return self._fetch()[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        self._mutate(lambda d: d.__setitem__(key, value))

    def __delitem__(self, key: KT) -> None:
        self._mutate(lambda d: d.__delitem__(key))

    def __iter__(self) -> Iterator[KT]:
        return iter(self._fetch())

    def __len__(self) -> int:
        return len(self._fetch())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {self._fetch()!r})"

    def snapshot(self) -> dict[KT, VT]:
        return self._fetch()

    def delete(self) -> None:
        self._dask_variable.delete()
