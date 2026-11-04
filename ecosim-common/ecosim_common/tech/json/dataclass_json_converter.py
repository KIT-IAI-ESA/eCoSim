from __future__ import annotations

import dataclasses
import datetime
import json
from enum import Enum
from types import UnionType
from typing import Any, ClassVar, Protocol, Union, get_args, get_origin, get_type_hints

from ecosim_common.communication.communication_protocol import CommunicationProtocol

_DATE_TIME_TYPES = (datetime.datetime, datetime.date, datetime.time)


class DataclassJsonConverter:
    """Converts a dataclass to/from a JSON string or dict.

    Supported field types: the JSON native types, datetime, Enum, nested dataclasses
    and lists, tuples and dictionaries of those. Writing is done by 'dataclasses.asdict',
    which leaves datetime and Enum values untouched, so '_json_default_converter' converts those.
    Reading restores the declared type of every field, so an entry survives the round trip.
    """

    @staticmethod
    def to_json_string(data: DataclassInstance) -> str:
        return json.dumps(dataclasses.asdict(data), default=DataclassJsonConverter._json_default_converter)

    @staticmethod
    def _json_default_converter(value: Any) -> Any:
        """Converts the values that 'json.dumps' cannot serialize on its own."""
        if isinstance(value, CommunicationProtocol):
            return value.serialized
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, _DATE_TIME_TYPES):
            return value.isoformat()
        raise TypeError(f"'{type(value)}' cannot be stored as JSON.")

    @staticmethod
    def of_json_string(
        entry_type: type,
        json_string: str,
    ) -> Any:
        return DataclassJsonConverter.of_dictionary(entry_type, json.loads(json_string))

    @staticmethod
    def of_dictionary(
        entry_type: type,
        data: dict[str, Any],
    ) -> Any:
        field_types = get_type_hints(entry_type)
        return entry_type(**{name: DataclassJsonConverter._of_value(field_types.get(name), value) for name, value in data.items()})

    @staticmethod
    def _of_value(
        value_type: Any,
        value: Any,
    ) -> Any:
        """Restores the declared type of a single field. A container is restored element wise by its first type argument."""
        if value is None:
            return None
        container_type = get_origin(value_type)
        if container_type in (Union, UnionType):
            return DataclassJsonConverter._of_value(DataclassJsonConverter._type_without_none(value_type), value)
        if container_type in (list, tuple, set):
            return container_type(DataclassJsonConverter._of_value(get_args(value_type)[0], element) for element in value)
        if isinstance(value_type, type) and dataclasses.is_dataclass(value_type):
            return DataclassJsonConverter.of_dictionary(value_type, value)
        if isinstance(value_type, type) and issubclass(value_type, CommunicationProtocol):
            return CommunicationProtocol.of(value)
        if isinstance(value_type, type) and issubclass(value_type, Enum):
            return value_type(value)
        if value_type in _DATE_TIME_TYPES:
            return value_type.fromisoformat(value)
        return value

    @staticmethod
    def _type_without_none(value_type: Any) -> Any:
        return next(argument for argument in get_args(value_type) if argument is not type(None))


class DataclassInstance(Protocol):
    """An instance of any dataclass.

    The dataclass decorator adds '__dataclass_fields__' to the decorated class, so this
    protocol matches every dataclass instance and nothing else.
    """

    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]
