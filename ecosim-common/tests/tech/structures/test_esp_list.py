import pickle
from typing import Any

import dask.distributed
import pytest
from distributed import Client
from ecosim_common.tech.structures.esp_list import ESPList
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


def test_init_simple() -> None:
    empty_list = ESPList[str].of_type(ESPStructureType.SIMPLE)
    assert len(empty_list) == 0

    initialized = ESPList[str].of_type(list_type=ESPStructureType.SIMPLE, data=["hello"])
    assert len(initialized) == 1


def test_init_dask(dask_client: Client) -> None:
    empty_list = ESPList[str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_list) == 0

    initialized = ESPList[str].of_type(list_type=ESPStructureType.DASK_VARIABLE, data=["hello"])
    assert len(initialized) == 1

    with_name = ESPList[str].of_type(
        list_type=ESPStructureType.DASK_VARIABLE,
        data=["hello"],
        dask_name="test_list",
    )
    assert len(with_name) == 1
    assert with_name._dask_variable.name == "test_list"  # type: ignore[attr-defined]  # noqa: SLF001


def test_init_dask_same_twice(dask_client: Client) -> None:
    empty_list = ESPList[str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_list) == 0

    with_name = ESPList[str].of_type(
        list_type=ESPStructureType.DASK_VARIABLE,
        data=["hello"],
        dask_name="test_list",
    )
    assert "hello" in with_name

    with_name = ESPList[str].of_type(
        list_type=ESPStructureType.DASK_VARIABLE,
        data=["eCoSim"],
        dask_name="test_list",
    )
    assert "hello" in with_name
    assert "eCoSim" not in with_name


def test_contains(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    assert "a" in esp_list
    assert "b" not in esp_list


def test_append(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    esp_list.append("a")
    assert len(esp_list) == 1


def test_append_duplicate_grows(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    esp_list.append("a")
    assert len(esp_list) == 2
    assert esp_list.get_snapshot() == ["a", "a"]


def test_insert(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "c"])
    esp_list.insert(1, "b")
    assert esp_list.get_snapshot() == ["a", "b", "c"]


def test_extend(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    esp_list.extend(["b", "c"])
    assert esp_list.get_snapshot() == ["a", "b", "c"]


def test_remove(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    esp_list.remove("a")
    assert len(esp_list) == 0


def test_remove_only_first_occurrence(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "a"])
    esp_list.remove("a")
    assert esp_list.get_snapshot() == ["a"]


def test_remove_missing_raises_value_error(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    with pytest.raises(ValueError):
        esp_list.remove("nope")


def test_pop_default(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    assert esp_list.pop() == "b"
    assert esp_list.get_snapshot() == ["a"]


def test_pop_index(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    assert esp_list.pop(0) == "a"
    assert esp_list.get_snapshot() == ["b", "c"]


def test_pop_empty_raises_index_error(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    with pytest.raises(IndexError):
        esp_list.pop()


def test_delitem(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    del esp_list[1]
    assert esp_list.get_snapshot() == ["a", "c"]


def test_delitem_slice(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c", "d"])
    del esp_list[1:3]
    assert esp_list.get_snapshot() == ["a", "d"]


def test_getitem_index(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    assert esp_list[0] == "a"
    assert esp_list[-1] == "c"


def test_getitem_slice(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    assert esp_list[0:2] == ["a", "b"]


def test_getitem_out_of_range_raises_index_error(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    with pytest.raises(IndexError):
        # noinspection PyStatementEffect
        esp_list[5]


def test_setitem_index(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    esp_list[0] = "z"
    assert esp_list.get_snapshot() == ["z", "b"]


def test_setitem_slice(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    esp_list[0:2] = ["x", "y"]
    assert esp_list.get_snapshot() == ["x", "y", "c"]


def test_transaction_append(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    with esp_list.transaction() as data:
        data.append("a")
        data.append("b")
    assert "a" in esp_list
    assert "b" in esp_list
    assert len(esp_list) == 2


def test_transaction_insert(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "c"])
    with esp_list.transaction() as data:
        data.insert(1, "b")
    assert esp_list.get_snapshot() == ["a", "b", "c"]


def test_transaction_remove(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    with esp_list.transaction() as data:
        data.remove("a")
    assert "a" not in esp_list
    assert len(esp_list) == 1


def test_transaction_remove_missing_raises_value_error(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    with pytest.raises(ValueError):
        with esp_list.transaction() as data:
            data.remove("nope")


def test_transaction_multiple_operations(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    with esp_list.transaction() as data:
        data.append("c")
        data.remove("a")
    assert esp_list.get_snapshot() == ["b", "c"]


def test_len_tracks_mutations(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    assert len(esp_list) == 0
    with esp_list.transaction() as data:
        data.append("a")
    assert len(esp_list) == 1
    with esp_list.transaction() as data:
        data.remove("a")
    assert len(esp_list) == 0


def test_iter_yields_elements_in_order(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    assert list(esp_list) == ["a", "b", "c"]


def test_clear(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    esp_list.clear()
    assert len(esp_list) == 0


def test_index(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    assert esp_list.index("b") == 1


def test_index_missing_raises_value_error(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    with pytest.raises(ValueError):
        esp_list.index("z")


def test_count(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "a", "b"])
    assert esp_list.count("a") == 2
    assert esp_list.count("z") == 0


def test_reversed(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b", "c"])
    assert list(reversed(esp_list)) == ["c", "b", "a"]


def test_equal_with_esp_list(esp_structure_type: ESPStructureType) -> None:
    list_1 = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    list_2 = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    assert list_1.get_snapshot() == list_2.get_snapshot()
    assert list_1 == list_2


def test_order_matters(esp_structure_type: ESPStructureType) -> None:
    lhs = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    rhs = ESPList[str].of_type(list_type=esp_structure_type, data=["b", "a"])
    assert lhs.get_snapshot() != rhs.get_snapshot()


def test_unhashable(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=[])
    with pytest.raises(TypeError):
        # noinspection PyUnhashable
        {esp_list}


@pytest.mark.parametrize("elem", [0, -1, "a", (1, 2), 3.14, None, True, [1, 2], {"k": "v"}])
def test_arbitrary_elements(esp_structure_type: ESPStructureType, elem: Any) -> None:
    esp_list = ESPList[object].of_type(list_type=esp_structure_type, data=[])
    with esp_list.transaction() as data:
        data.append(elem)
    assert elem in esp_list


def test_roundtrip_through_list(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    restored = ESPList[str].of_type(list_type=esp_structure_type, data=list(esp_list))
    assert restored.get_snapshot() == esp_list.get_snapshot()


def test_list_unpacking(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    assert [*esp_list] == ["a", "b"]


def test_mutation_during_iteration_raises_no_error(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a", "b"])
    for e in esp_list:
        with esp_list.transaction() as data:
            data.append(f"{e}!")


def test_snapshot_is_copy(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[str].of_type(list_type=esp_structure_type, data=["a"])
    snap = esp_list.get_snapshot()
    snap.append("b")
    assert "b" not in esp_list


def test_pickle(dask_client: dask.distributed.Client) -> None:
    esp_list = ESPList[str].of_type(list_type=ESPStructureType.DASK_VARIABLE, data=["a", "b"])
    esp_list.append("c")

    restored = pickle.loads(pickle.dumps(esp_list))

    assert isinstance(restored, ESPList)
    assert len(restored) == 3
    assert "c" in esp_list

    restored.append("d")
    esp_list.append("e")

    assert "d" in esp_list
    assert "d" in restored
    assert "e" in esp_list
    assert "e" in restored


def test_esp_list_dask_different_name_on_default(dask_client: Client) -> None:
    esp_list_1 = ESPList[str].of_type(list_type=ESPStructureType.DASK_VARIABLE, data=["a", "b"])
    esp_list_2 = ESPList[str].of_type(list_type=ESPStructureType.DASK_VARIABLE, data=["a", "b"])
    esp_list_3 = ESPList[str].of_type(list_type=ESPStructureType.DASK_VARIABLE, data=["a", "b"])

    assert esp_list_1._dask_variable.name is not None  # type: ignore[attr-defined]  # noqa: SLF001
    assert esp_list_2._dask_variable.name is not None  # type: ignore[attr-defined]  # noqa: SLF001
    assert esp_list_3._dask_variable.name is not None  # type: ignore[attr-defined]  # noqa: SLF001

    assert esp_list_1._dask_variable.name != esp_list_2._dask_variable.name  # type: ignore[attr-defined]  # noqa: SLF001
    assert esp_list_1._dask_variable.name != esp_list_3._dask_variable.name  # type: ignore[attr-defined]  # noqa: SLF001
    assert esp_list_2._dask_variable.name != esp_list_3._dask_variable.name  # type: ignore[attr-defined]  # noqa: SLF001
