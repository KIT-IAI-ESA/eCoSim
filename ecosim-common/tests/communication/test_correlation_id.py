import pytest

from ecosim_common.communication.correlation_id import CorrelationId


def test_happy_path() -> None:
    correlation_id = CorrelationId.of_int(24984)
    assert correlation_id.to_int() == 24984
    assert correlation_id == CorrelationId.of_int(24984)


def test_less_than_min() -> None:
    with pytest.raises(ValueError):
        CorrelationId.of_int(-1)


def test_greater_than_max() -> None:
    with pytest.raises(ValueError):
        CorrelationId.of_int(4_294_967_295 + 1)
