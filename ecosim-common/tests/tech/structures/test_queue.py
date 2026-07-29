# --- init ---
import pytest
from distributed import Client
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


def test_init_simple() -> None:
    empty_queue = ESPQueue[str].of_type(ESPStructureType.SIMPLE)
    assert len(empty_queue) == 0
    initialized = ESPQueue[str].of_type(queue_type=ESPStructureType.SIMPLE, data=["hello"])
    assert len(initialized) == 1


def test_init_dask(dask_client: Client) -> None:
    empty_queue = ESPQueue[str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_queue) == 0
    initialized = ESPQueue[str].of_type(queue_type=ESPStructureType.DASK_VARIABLE, data=["hello"])
    assert len(initialized) == 1
    with_name = ESPQueue[str].of_type(
        queue_type=ESPStructureType.DASK_VARIABLE,
        data=["hello"],
        dask_name="test_queue",
    )
    assert len(with_name) == 1
    assert with_name._dask_queue.name == "test_queue"  # type: ignore[attr-defined]  # noqa: SLF001


def test_init_dask_same_twice(dask_client: Client) -> None:
    first = ESPQueue[str].of_type(
        queue_type=ESPStructureType.DASK_VARIABLE,
        data=["hello"],
        dask_name="test_queue",
    )
    second = ESPQueue[str].of_type(
        queue_type=ESPStructureType.DASK_VARIABLE,
        data=["eCoSim"],
        dask_name="test_queue",
    )
    # named dask queues are shared and 'data' appends -> both items are in the same queue
    assert len(first) == 2
    assert len(second) == 2
    assert first.pop() == "hello"
    assert second.pop() == "eCoSim"
    assert len(first) == 0
    assert len(second) == 0


def test_push(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=[])
    esp_queue.push("a")
    assert len(esp_queue) == 1


def test_pop_is_fifo(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=["a", "b"])
    assert esp_queue.pop() == "a"
    assert esp_queue.pop() == "b"
    assert len(esp_queue) == 0


def test_pop_empty_raises_timeout_error(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=[])
    with pytest.raises(TimeoutError):
        esp_queue.pop(timeout=0)


def test_pop_or_none_empty(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=[])
    assert esp_queue.pop_or_none(timeout=0) is None


def test_push_many(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=[])
    esp_queue.push_many(["a", "b"])
    assert len(esp_queue) == 2


def test_pop_all(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=["a", "b"])
    assert esp_queue.pop_all() == ["a", "b"]
    assert len(esp_queue) == 0


def test_clear(esp_structure_type: ESPStructureType) -> None:
    esp_queue = ESPQueue[str].of_type(queue_type=esp_structure_type, data=["a"])
    esp_queue.clear()
    assert len(esp_queue) == 0


def test_using_as_bool_evaluation(esp_structure_type: ESPStructureType) -> None:
    assert not ESPQueue[str].of_type(queue_type=esp_structure_type, data=[])
    assert ESPQueue[str].of_type(queue_type=esp_structure_type, data=["a"])
