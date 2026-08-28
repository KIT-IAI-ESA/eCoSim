"""
The dask 'Queue' payload is serialized with msgpack. An object msgpack cannot encode makes
'distributed' throw away the whole encoded message, log 'falling back to pickle' and encode it
a second time through a slower per-object path - on the sender *and* on the scheduler that
sends the payload back. Pushing bytes keeps every payload on the fast path.
"""

import logging
from dataclasses import dataclass

import pytest
from distributed import Client
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

_PICKLE_FALLBACK_LOGGER = "distributed.protocol.core"
_PICKLE_FALLBACK_MESSAGE = "falling back to pickle"


@dataclass(frozen=True)
class _NotMsgpackSerializable:
    """A plain dataclass is exactly what 'ClientMessage' and 'InterfaceValueHistoryEntry' are."""

    value: int


def test_push_and_pop_does_not_fall_back_to_pickle(
    dask_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue = ESPQueue[_NotMsgpackSerializable].of_type(ESPStructureType.DASK_VARIABLE)
    with caplog.at_level(logging.INFO, logger=_PICKLE_FALLBACK_LOGGER):
        queue.push(_NotMsgpackSerializable(value=42))
        queue.pop(timeout=5)
    assert _PICKLE_FALLBACK_MESSAGE not in caplog.text


def test_push_and_pop_keeps_the_pushed_object(
    dask_client: Client,
    esp_structure_type: ESPStructureType,
) -> None:
    queue = ESPQueue[_NotMsgpackSerializable].of_type(esp_structure_type)
    queue.push(_NotMsgpackSerializable(value=7))
    assert queue.pop(timeout=5) == _NotMsgpackSerializable(value=7)


def test_init_data_keeps_the_pushed_objects(
    esp_structure_type: ESPStructureType,
) -> None:
    queue = ESPQueue[_NotMsgpackSerializable].of_type(
        queue_type=esp_structure_type,
        data=[_NotMsgpackSerializable(value=1), _NotMsgpackSerializable(value=2)],
    )
    assert queue.pop_all() == [_NotMsgpackSerializable(value=1), _NotMsgpackSerializable(value=2)]


def test_pop_all_keeps_the_pushed_objects(
    esp_structure_type: ESPStructureType,
) -> None:
    queue = ESPQueue[_NotMsgpackSerializable].of_type(esp_structure_type)
    queue.push_many([_NotMsgpackSerializable(value=3), _NotMsgpackSerializable(value=4)])
    assert queue.pop_all() == [_NotMsgpackSerializable(value=3), _NotMsgpackSerializable(value=4)]


def test_bytes_survive_the_round_trip(
    esp_structure_type: ESPStructureType,
) -> None:
    """'DaskChannel' pushes raw bytes - they must not be confused with the serialized envelope."""
    queue = ESPQueue[bytes].of_type(esp_structure_type)
    queue.push(b"\x00\x01raw")
    assert queue.pop(timeout=5) == b"\x00\x01raw"
