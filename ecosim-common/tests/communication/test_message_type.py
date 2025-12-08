from ecosim_common.communication.message_type import MessageType


def test_ensure_deserialization() -> None:
    for message_type in MessageType:
        assert message_type == MessageType.of_int(message_type.value)


def test_less_than_min_deserialization() -> None:
    assert MessageType.UNKNOWN == MessageType.of_int(-1)


def test_greater_than_max_deserialization() -> None:
    assert MessageType.UNKNOWN == MessageType.of_int(266)


def test_unknown_type() -> None:
    taken_values = [message_type.to_int() for message_type in MessageType]
    for number in range(0, 256):
        if number not in taken_values:
            assert MessageType.UNKNOWN == MessageType.of_int(number)
