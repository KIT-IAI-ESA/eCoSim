import pickle
from typing import Any

import dask.distributed
import pytest
from distributed import Client
from ecosim_common.tech.structures.esp_set import ESPSet
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


def test_init_simple() -> None:
    empty_set = ESPSet[str].of_type(ESPStructureType.SIMPLE)
    assert len(empty_set) == 0

    initialized = ESPSet[str].of_type(set_type=ESPStructureType.SIMPLE, data={"hello"})
    assert len(initialized) == 1


def test_init_dask(dask_client: Client) -> None:
    empty_set = ESPSet[str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_set) == 0

    initialized = ESPSet[str].of_type(set_type=ESPStructureType.DASK_VARIABLE, data={"hello"})
    assert len(initialized) == 1

    with_name = ESPSet[str].of_type(
        set_type=ESPStructureType.DASK_VARIABLE,
        data={"hello"},
        dask_name="test_set",
    )
    assert len(with_name) == 1


def test_init_dask_same_twice(dask_client: Client) -> None:
    empty_set = ESPSet[str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_set) == 0

    with_name = ESPSet[str].of_type(
        set_type=ESPStructureType.DASK_VARIABLE,
        data={"hello"},
        dask_name="test_set",
    )
    assert "hello" in with_name

    with_name = ESPSet[str].of_type(
        set_type=ESPStructureType.DASK_VARIABLE,
        data={"eCoSim"},
        dask_name="test_set",
    )
    assert "hello" in with_name
    assert "eCoSim" not in with_name


# --- __contains__ ---


def test_contains(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    assert "a" in esp_set
    assert "b" not in esp_set


def test_contains_unhashable_raises_typeerror(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[Any].of_type(set_type=esp_structure_type, data=set())
    with pytest.raises(TypeError):
        ["a"] in esp_set


def test_add(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data=set())
    esp_set.add("a")
    assert len(esp_set) == 1


def test_discard(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    esp_set.discard("a")
    assert len(esp_set) == 0


def test_remove(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    esp_set.remove("a")
    assert len(esp_set) == 0


def test_transaction_add(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data=set())
    with esp_set.transaction() as s:
        s.add("a")
    assert "a" in esp_set
    assert len(esp_set) == 1


def test_transaction_add_duplicate_no_growth(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    with esp_set.transaction() as s:
        s.add("a")
    assert len(esp_set) == 1


def test_transaction_discard(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    with esp_set.transaction() as s:
        s.discard("a")
    assert "a" not in esp_set
    assert len(esp_set) == 1


def test_transaction_discard_missing_no_error(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data=set())
    with esp_set.transaction() as s:
        s.discard("nope")
    assert len(esp_set) == 0


def test_transaction_remove_missing_raises_keyerror(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data=set())
    with pytest.raises(KeyError):
        with esp_set.transaction() as s:
            s.remove("nope")


# --- __len__ / __iter__ ---


def test_len_tracks_mutations(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data=set())
    assert len(esp_set) == 0
    with esp_set.transaction() as s:
        s.add("a")
    assert len(esp_set) == 1
    with esp_set.transaction() as s:
        s.discard("a")
    assert len(esp_set) == 0


def test_iter_yields_elements(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert set(esp_set) == {"a", "b"}


# --- clear ---


def test_clear(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    esp_set.clear()
    assert len(esp_set) == 0


# --- Set ABC mixin operators (read-only) ---


def test_le_subset(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    assert esp_set <= {"a", "b"}
    assert not esp_set <= {"b"}


def test_ge_superset(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert esp_set >= {"a"}
    assert not esp_set >= {"c"}


def test_and_intersection(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert (esp_set & {"b", "c"}) == {"b"}


def test_or_union(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    assert (esp_set | {"b"}) == {"a", "b"}


def test_sub_difference(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert (esp_set - {"a"}) == {"b"}


def test_xor_symmetric_difference(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert (esp_set ^ {"b", "c"}) == {"a", "c"}


def test_isdisjoint(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    assert esp_set.isdisjoint({"b"})
    assert not esp_set.isdisjoint({"a"})


# --- equality ---


def test_eq_with_set(esp_structure_type: ESPStructureType) -> None:
    assert ESPSet[str].of_type(set_type=esp_structure_type, data={"a"}) == {"a"}
    assert ESPSet[str].of_type(set_type=esp_structure_type, data={"a"}) != {"b"}


def test_eq_with_esp_set(esp_structure_type: ESPStructureType) -> None:
    lhs = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    rhs = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    assert lhs == rhs


def test_eq_ignores_order(esp_structure_type: ESPStructureType) -> None:
    lhs = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    rhs = ESPSet[str].of_type(set_type=esp_structure_type, data={"b", "a"})
    assert lhs == rhs


def test_not_eq_other_type(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    assert esp_set != "not a set"


def test_unhashable(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data=set())
    with pytest.raises(TypeError):
        {esp_set}


# --- element flexibility ---


@pytest.mark.parametrize("elem", [0, -1, "a", (1, 2), 3.14, None, True, frozenset({1})])
def test_arbitrary_hashable_elements(esp_structure_type: ESPStructureType, elem: object) -> None:
    esp_set = ESPSet[object].of_type(set_type=esp_structure_type, data=set())
    with esp_set.transaction() as s:
        s.add(elem)
    assert elem in esp_set


def test_int_and_bool_elements_collide(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[int].of_type(set_type=esp_structure_type, data=set())
    with esp_set.transaction() as s:
        s.add(1)
        s.add(True)
    assert len(esp_set) == 1


# --- integration ---


def test_roundtrip_through_set(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert ESPSet[str].of_type(set_type=esp_structure_type, data=set(esp_set)) == esp_set


def test_set_unpacking(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    assert {*esp_set} == {"a", "b"}


def test_mutation_during_iteration_raises_no_error(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    for e in esp_set:
        with esp_set.transaction() as s:
            s.add(f"{e}!")


def test_snapshot_is_copy(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a"})
    snap = esp_set.get_snapshot()
    snap.add("b")
    assert "b" not in esp_set


def test_transaction_multiple_ops(esp_structure_type: ESPStructureType) -> None:
    esp_set = ESPSet[str].of_type(set_type=esp_structure_type, data={"a", "b"})
    with esp_set.transaction() as s:
        s.add("c")
        s.discard("a")
    assert esp_set.get_snapshot() == {"b", "c"}


def test_pickle(dask_client: dask.distributed.Client) -> None:
    esp_set = ESPSet[str].of_type(set_type=ESPStructureType.DASK_VARIABLE, data={"a", "b"})
    esp_set.add("c")
    restored = pickle.loads(pickle.dumps(esp_set))
    assert isinstance(restored, ESPSet)
    assert len(restored) == 3

    restored.add("d")
    esp_set.add("e")
    assert "d" in restored
    assert "d" in esp_set
    assert "e" in restored
    assert "e" in esp_set

    assert restored._dask_variable.name == esp_set._dask_variable.name  # type: ignore[attr-defined]  # noqa: SLF001
    assert restored._lock._name == esp_set._lock._name  # type: ignore[attr-defined]  # noqa: SLF001
