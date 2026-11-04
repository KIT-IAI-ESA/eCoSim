from __future__ import annotations

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.json.dataclass_json_converter import DataclassJsonConverter

from tests.tech.json.json_converter_test_setup import (
    TIMESTAMP,
    Entry,
    FlatEntry,
    OptionalEntry,
    ProtocolEntry,
    Quality,
    Reading,
    SetEntry,
    create_entry,
    round_tripped_to_and_of_json_string,
    to_json_string_then_json_loads,
)

# --- writing a dataclass as a JSON string ---


def test_every_field_of_the_dataclass_is_written() -> None:
    assert set(to_json_string_then_json_loads(create_entry()).keys()) == {"timestamp", "readings", "quality", "tags", "lookup"}


def test_a_datetime_is_written_as_an_iso_string() -> None:
    assert to_json_string_then_json_loads(create_entry())["timestamp"] == TIMESTAMP.isoformat()


def test_an_enum_is_written_as_its_value() -> None:
    assert to_json_string_then_json_loads(create_entry())["quality"] == "good"


def test_a_nested_dataclass_is_written_as_a_json_object() -> None:
    assert to_json_string_then_json_loads(create_entry())["readings"] == [{"name": "room_temperature", "value": 293.15}]


def test_a_dictionary_field_is_written_as_a_json_object() -> None:
    assert to_json_string_then_json_loads(create_entry())["lookup"] == {"delta_t": 60.0}


def test_the_json_string_is_a_single_line() -> None:
    assert "\n" not in DataclassJsonConverter.to_json_string(create_entry())


def test_writing_a_value_that_json_does_not_support_fails() -> None:
    with pytest.raises(TypeError):
        DataclassJsonConverter.to_json_string(SetEntry(values={"house"}))


def test_a_communication_protocol_is_written_as_its_serialized_name() -> None:
    assert to_json_string_then_json_loads(ProtocolEntry(protocol=CommunicationProtocol.TCP_SOCKET)) == {"protocol": "tcp_socket"}


# --- reading a dataclass back ---


def test_a_dataclass_with_json_native_fields_survives_the_round_trip() -> None:
    flat_entry = FlatEntry(name="house", value=293.15, comment="a comment")

    assert round_tripped_to_and_of_json_string(FlatEntry, flat_entry) == flat_entry


def test_of_dictionary_builds_the_entry_from_the_dictionary() -> None:
    restored = DataclassJsonConverter.of_dictionary(FlatEntry, {"name": "house", "value": 293.15})

    assert restored == FlatEntry(name="house", value=293.15)


def test_a_missing_optional_field_falls_back_to_the_default() -> None:
    restored = DataclassJsonConverter.of_dictionary(FlatEntry, {"name": "house", "value": 293.15})

    assert restored.comment is None


def test_reading_a_field_that_the_dataclass_does_not_have_fails() -> None:
    with pytest.raises(TypeError):
        DataclassJsonConverter.of_dictionary(FlatEntry, {"name": "house", "value": 293.15, "unknown": 1})


# --- reading restores the declared field types ---


def test_a_datetime_field_is_restored_as_a_datetime() -> None:
    assert round_tripped_to_and_of_json_string(Entry, create_entry()).timestamp == TIMESTAMP


def test_an_enum_field_is_restored_as_an_enum() -> None:
    assert round_tripped_to_and_of_json_string(Entry, create_entry()).quality is Quality.GOOD


def test_a_communication_protocol_field_is_restored_as_a_communication_protocol(communication_protocol: CommunicationProtocol) -> None:
    restored = round_tripped_to_and_of_json_string(ProtocolEntry, ProtocolEntry(protocol=communication_protocol))

    assert restored.protocol is communication_protocol


def test_a_nested_dataclass_field_is_restored_as_a_dataclass() -> None:
    assert round_tripped_to_and_of_json_string(Entry, create_entry()).readings[0] == Reading(name="room_temperature", value=293.15)


def test_a_tuple_field_is_restored_as_a_tuple_and_not_as_a_list() -> None:
    assert isinstance(round_tripped_to_and_of_json_string(Entry, create_entry()).readings, tuple)


def test_a_dictionary_field_is_restored_as_a_dictionary() -> None:
    assert round_tripped_to_and_of_json_string(Entry, create_entry()).lookup == {"delta_t": 60.0}


def test_an_optional_datetime_is_restored_as_a_datetime() -> None:
    optional_entry = OptionalEntry(timestamp=TIMESTAMP)

    assert round_tripped_to_and_of_json_string(OptionalEntry, optional_entry) == optional_entry


def test_an_optional_field_that_is_none_stays_none() -> None:
    assert round_tripped_to_and_of_json_string(OptionalEntry, OptionalEntry(timestamp=None)).timestamp is None


def test_an_entry_with_not_json_native_fields_is_equal_after_the_round_trip() -> None:
    assert round_tripped_to_and_of_json_string(Entry, create_entry()) == create_entry()


def test_calling_method_on_class_and_nested_class() -> None:
    restored = round_tripped_to_and_of_json_string(Entry, create_entry())
    assert restored.test_method() == Quality.GOOD
    assert restored.readings[0].test_method() == "room_temperature"
