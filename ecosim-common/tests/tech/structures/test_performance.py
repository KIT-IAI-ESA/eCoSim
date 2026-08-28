from typing import Any

from ecosim_common.tech.structures.esp_list import ESPList
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


def test_transaction_transaction_append_performance(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[Any].of_type(
        list_type=esp_structure_type,
        data=[],
    )
    with esp_list.transaction() as data:
        for i in range(1000):
            data.append(i)
    assert len(esp_list) == 1000


def test_append_performance(esp_structure_type: ESPStructureType) -> None:
    esp_list = ESPList[Any].of_type(
        list_type=esp_structure_type,
        data=[],
    )
    for i in range(1000):
        with esp_list.transaction() as data:
            data.append(i)
    assert len(esp_list) == 1000


def test_append_performance_large(esp_structure_type: ESPStructureType) -> None:
    base_string = "hello world! "
    encoded_base_size = len(base_string.encode("utf-8"))
    mb_15 = 15 * 1024 * 1024
    repetitions = mb_15 // encoded_base_size + 1
    final_string = base_string * repetitions

    esp_list = ESPList[Any].of_type(
        list_type=esp_structure_type,
        data=[],
    )
    for i in range(10):
        with esp_list.transaction() as data:
            data.append(final_string)
    assert len(esp_list) == 10
