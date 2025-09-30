from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CorrelationId:
    """
    The CorrelationID is mainly used for correlating channel messages.
    The internal representation are values from 0 to 4.294.967.295.
    This restriction will ensure certainty about the byte size and encoding for underlying protocols.
    """

    _value: int = field()

    def __post_init__(self) -> None:
        if self._value < 0 or self._value > 4294967295:
            raise ValueError(f"Value must be between 0 and 4294967295 but was {self._value}.")

    @staticmethod
    def of_int(value: int) -> CorrelationId:
        return CorrelationId(_value=value)

    @staticmethod
    def default_id() -> CorrelationId:
        return CorrelationId(_value=0)

    def to_int(self) -> int:
        """
        :return: unsigned int32 (i.e. 4 bytes or values from 0 to 4.294.967.295)
        """
        return self._value
