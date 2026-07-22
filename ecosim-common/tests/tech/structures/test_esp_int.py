from ecosim_common.tech.structures.esp_int import ESPInt
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


def test_init(esp_structure_type: ESPStructureType) -> None:
    default_init = ESPInt.of_type(structure_type=esp_structure_type)
    assert default_init.get() == 0


def test_init_value(esp_structure_type: ESPStructureType) -> None:
    init = ESPInt.of_type(structure_type=esp_structure_type, value=33)
    assert init.get() == 33


def test_get(esp_structure_type: ESPStructureType) -> None:
    esp_int = ESPInt.of_type(structure_type=esp_structure_type)
    assert esp_int.get() == 0


def test_set(esp_structure_type: ESPStructureType) -> None:
    esp_int = ESPInt.of_type(structure_type=esp_structure_type)
    esp_int.set(3344)
    assert esp_int.get() == 3344


def test_increment(esp_structure_type: ESPStructureType) -> None:
    esp_int = ESPInt.of_type(
        structure_type=esp_structure_type,
        value=111,
    )
    esp_int.increment()
    assert esp_int.get() == 112


def test_increment_value(esp_structure_type: ESPStructureType) -> None:
    esp_int = ESPInt.of_type(
        structure_type=esp_structure_type,
        value=111,
    )
    esp_int.increment(222)
    assert esp_int.get() == 333
