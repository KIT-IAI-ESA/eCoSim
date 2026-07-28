import pickle
from typing import Any, ItemsView, KeysView, ValuesView

import distributed
import pytest
from distributed import Client
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


def test_init_simple() -> None:
    empty_map = ESPMap[str, str].of_type(ESPStructureType.SIMPLE)
    assert len(empty_map) == 0

    initialized = ESPMap[str, str].of_type(map_type=ESPStructureType.SIMPLE, data={"hello": "world"})
    assert len(initialized) == 1


def test_init_dask(dask_client: Client) -> None:
    empty_map = ESPMap[str, str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_map) == 0

    initialized = ESPMap[str, str].of_type(map_type=ESPStructureType.DASK_VARIABLE, data={"hello": "world"})
    assert len(initialized) == 1

    with_name = ESPMap[str, str].of_type(
        map_type=ESPStructureType.DASK_VARIABLE,
        data={"hello": "world"},
        dask_name="test_map",
    )
    assert len(with_name) == 1


def test_init_dask_same_twice(dask_client: Client) -> None:
    empty_map = ESPMap[str, str].of_type(ESPStructureType.DASK_VARIABLE)
    assert len(empty_map) == 0

    with_name = ESPMap[str, str].of_type(
        map_type=ESPStructureType.DASK_VARIABLE,
        data={"hello": "world"},
        dask_name="test_map",
    )
    assert with_name["hello"] == "world"

    with_name = ESPMap[str, str].of_type(
        map_type=ESPStructureType.DASK_VARIABLE,
        data={"hello": "eCoSim"},
        dask_name="test_map",
    )
    assert with_name["hello"] == "world"


def test_getitem(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert esp_map["a"] == 1


def test_getitem_missing_raises_key_error(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={})
    with pytest.raises(KeyError):
        # noinspection PyStatementEffect
        esp_map["nope"]


def test_getitem_unhashable_raises_type_error(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={})
    with pytest.raises(TypeError):
        # noinspection PyStatementEffect
        esp_map[["a"]]  # type: ignore[index]


def test_setitem_new_key(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={})
    esp_map["a"] = 1
    assert esp_map["a"] == 1


def test_setitem_overwrites(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    esp_map["a"] = 2
    assert esp_map["a"] == 2
    assert len(esp_map) == 1


def test_setitem_none_value(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, None].of_type(map_type=esp_structure_type, data={})
    esp_map["a"] = None
    assert esp_map["a"] is None
    assert "a" in esp_map


def test_delete_item(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    del esp_map["a"]
    assert "a" not in esp_map
    assert len(esp_map) == 1


def test_delete_item_missing_raises_key_error(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={})
    with pytest.raises(KeyError):
        del esp_map["nope"]


def test_len_tracks_mutations(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={})
    assert len(esp_map) == 0
    esp_map["a"] = 1
    assert len(esp_map) == 1
    del esp_map["a"]
    assert len(esp_map) == 0


def test_iter_yields_keys(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    assert list(esp_map) == ["a", "b"]


def test_iter_preserves_insertion_order(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, str].of_type(map_type=esp_structure_type, data={})
    for k in "cab":
        esp_map[k] = k
    assert list(esp_map) == ["c", "a", "b"]


def test_contains(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert "a" in esp_map
    assert "b" not in esp_map


def test_get(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert esp_map.get("a") == 1
    assert esp_map.get("b") is None
    assert esp_map.get("b", 99) == 99


def test_keys_values_items(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    assert isinstance(esp_map.keys(), KeysView)
    assert isinstance(esp_map.values(), ValuesView)
    assert isinstance(esp_map.items(), ItemsView)
    assert list(esp_map.keys()) == ["a", "b"]
    assert list(esp_map.values()) == [1, 2]
    assert list(esp_map.items()) == [("a", 1), ("b", 2)]


def test_pop(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert esp_map.pop("a") == 1
    assert len(esp_map) == 0
    assert esp_map.pop("a", 99) == 99
    with pytest.raises(KeyError):
        esp_map.pop("a")


def test_update(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    esp_map.update({"b": 2})
    esp_map.update([("c", 3)])
    esp_map.update(e=5)
    assert dict(esp_map) == {"a": 1, "b": 2, "c": 3, "e": 5}


def test_clear(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    esp_map.clear()
    assert len(esp_map) == 0


def test_eq_with_dict(esp_structure_type: ESPStructureType) -> None:
    assert ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1}) == {"a": 1}
    assert ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1}) != {"a": 2}


def test_eq_with_esp_map(esp_structure_type: ESPStructureType) -> None:
    lhs = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    rhs = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert lhs == rhs


def test_eq_ignores_order(esp_structure_type: ESPStructureType) -> None:
    lhs = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    rhs = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"b": 2, "a": 1})
    assert lhs == rhs


def test_not_eq_other_type(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert esp_map != "not a mapping"


def test_unhashable(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={})
    with pytest.raises(TypeError):
        # noinspection PyUnhashable,PyStatementEffect
        {esp_map}


# --- key/value flexibility ---


@pytest.mark.parametrize("key", [0, -1, "a", (1, 2), 3.14, None, True, frozenset({1})])
def test_arbitrary_hashable_keys(esp_structure_type: ESPStructureType, key: object) -> None:
    esp_map = ESPMap[object, str].of_type(map_type=esp_structure_type, data={})
    esp_map[key] = "v"
    assert esp_map[key] == "v"


def test_int_and_bool_keys_collide(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[int, str].of_type(map_type=esp_structure_type, data={})
    esp_map[1] = "int"
    esp_map[True] = "bool"
    assert len(esp_map) == 1
    assert esp_map[1] == "bool"


# --- integration ---


def test_roundtrip_through_dict(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    assert ESPMap[str, int].of_type(map_type=esp_structure_type, data=dict(esp_map)) == esp_map


def test_dict_unpacking(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    assert {**esp_map} == {"a": 1, "b": 2}


def test_kwargs_unpacking(esp_structure_type: ESPStructureType) -> None:
    def f(**kw: int) -> dict[str, int]:
        return kw

    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1})
    assert f(**esp_map) == {"a": 1}


def test_mutation_during_iteration_raises_no_error(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=esp_structure_type, data={"a": 1, "b": 2})
    for k in esp_map:
        esp_map[f"{k}!"] = 1


def test_map_to_object_with_transaction(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, Any].of_type(map_type=esp_structure_type, data={"a": {"test": None}, "b": {"test": None}})
    for k in esp_map:
        with esp_map.transaction() as map:
            # noinspection PyTypeChecker
            map[k]["test"] = "Hello world"
    assert esp_map.get_snapshot() == {"a": {"test": "Hello world"}, "b": {"test": "Hello world"}}


def test_map_to_object_with_list_with_transaction(esp_structure_type: ESPStructureType) -> None:
    esp_map = ESPMap[str, Any].of_type(map_type=esp_structure_type, data={"a": {"test": []}, "b": {"test": []}})
    for k in esp_map:
        with esp_map.transaction() as map:
            map[k]["test"].append("Hello world")
    assert esp_map.get_snapshot() == {"a": {"test": ["Hello world"]}, "b": {"test": ["Hello world"]}}


def test_keys_values_items_after_pickle(dask_client: distributed.Client) -> None:
    esp_map = ESPMap[str, int].of_type(map_type=ESPStructureType.DASK_VARIABLE, data={"a": 1, "b": 2})
    esp_map["c"] = 3
    restored = pickle.loads(pickle.dumps(esp_map))
    assert isinstance(restored.keys(), KeysView)
    assert isinstance(restored.values(), ValuesView)
    assert isinstance(restored.items(), ItemsView)
    assert list(restored.keys()) == ["a", "b", "c"]
    assert list(restored.values()) == [1, 2, 3]
    assert list(restored.items()) == [("a", 1), ("b", 2), ("c", 3)]

    restored["d"] = 4
    esp_map["e"] = 5

    assert "d" in restored
    assert "d" in esp_map
    assert "e" in restored
    assert "e" in esp_map


def test_pickle_nested_map(dask_client: distributed.Client) -> None:
    esp_map = ESPMap[str, dict[str, int]].of_type(map_type=ESPStructureType.DASK_VARIABLE, data={"a": {"a.1": 1}, "b": {"b.1": 2}})
    esp_map["c"] = {"c.1": 1}
    restored = pickle.loads(pickle.dumps(esp_map))

    assert "b" in restored
    assert {"b.1": 2} == restored["b"]
