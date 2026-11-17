from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace

from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ModelInterfaceServer

type ColumnValue = float | None


@dataclass(frozen=True)
class ResultColumn:
    """Describes one column of a result table, an interface or one position of an array interface."""

    simulator_name: str
    interface_name: str
    # None for result files without the run's simulation.json
    interface_type: InterfaceType | None
    unit: str = ""
    index: tuple[int, ...] = ()

    @staticmethod
    def of_interface(interface: ModelInterfaceServer) -> ResultColumn:
        return ResultColumn(
            simulator_name=interface.simulator_interface_id.simulator_name,
            interface_name=interface.name,
            interface_type=interface.type,
            unit=interface.unit or "",
        )

    @property
    def name(self) -> str:
        positions = "".join(f"[{position}]" for position in self.index)
        return f"{self.simulator_name}.{self.interface_name}{positions}"

    @property
    def is_input(self) -> bool:
        return self.interface_type is InterfaceType.INPUT

    def matches(self, name: str, ignore_case: bool = False) -> bool:
        """Returns whether the name is the column, its simulator or its array."""
        own_name = self.name.lower() if ignore_case else self.name
        return own_name == name or own_name.startswith(f"{name}.") or own_name.startswith(f"{name}[")

    def for_index(self, index: tuple[int, ...]) -> ResultColumn:
        return replace(self, index=index)


def numbers_by_index(value: InterfaceValue, index: tuple[int, ...] = ()) -> Iterator[tuple[tuple[int, ...], ColumnValue]]:
    if isinstance(value, list):
        for position, item in enumerate(value):
            yield from numbers_by_index(value=item, index=(*index, position))
        return
    yield index, float(value) if isinstance(value, (int, float)) else None
