import pytest
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_server.client.client_message import ClientMessage
from ecosim_server.client.client_message_buffer import ClientMessageBuffer


def _make_message(msg_type: MessageType = MessageType.SIMULATION_STEP, correlation_id: int = 1, payload: str = "payload-1") -> ESPChannelMessage:
    return ESPChannelMessageJson(
        _type=msg_type,
        _correlation_id=CorrelationId.of_int(correlation_id),
        _payload=payload,
    )


def _make_client_id(model: str = "model") -> ClientID:
    return ClientID(model_name=model, simulator_name="simulator")


def _make_queue(communication_protocol: CommunicationProtocol) -> ESPQueue[ClientMessage]:
    return ESPQueue.of_communication_protocol(communication_protocol)


def test_add_without_subscription_appends_to_buffer(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)

    buffer.add(client_id, message)

    result = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert len(result) == 1
    assert result[0].client_id == client_id


def test_add_writes_into_the_subscribed_queue(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    queue = buffer.subscribe((client_id,), (message.type(),))

    buffer.add(client_id, message)

    assert queue is not None
    assert queue.qsize() == 1
    assert buffer.get_and_delete_of((client_id,), (message.type(),)) == []


def test_add_keeps_the_message_order(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    queue = buffer.subscribe((client_id,), (MessageType.SIMULATION_STEP,))

    for correlation_id in range(10):
        buffer.add(client_id, _make_message(correlation_id=correlation_id))

    assert queue is not None
    received = [message.message.correlation_id().to_int() for message in queue.pop_all()]
    assert received == list(range(10))


def test_add_ignores_a_subscription_of_another_client(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id("client-1")
    other_client_id = _make_client_id("client-2")
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    queue = buffer.subscribe((other_client_id,), (message.type(),))

    buffer.add(client_id, message)

    assert queue is not None
    assert queue.qsize() == 0
    assert len(buffer.get_and_delete_of((client_id,), (message.type(),))) == 1


def test_subscribe_drains_pre_existing_buffered_messages(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)

    queue = buffer.subscribe((client_id,), (message.type(),))

    assert queue is not None
    assert queue.qsize() == 1
    assert buffer.get_and_delete_of((client_id,), (message.type(),)) == []


def test_subscribe_twice_throws_error(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.subscribe((client_id,), (MessageType.PING,))
    with pytest.raises(RuntimeError):
        buffer.subscribe((client_id,), (MessageType.PING,))


def test_unsubscribe_then_message_is_buffered(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    queue = buffer.subscribe((client_id,), (message.type(),))
    buffer.unsubscribe((client_id,), (message.type(),))

    buffer.add(client_id, message)

    assert queue is not None
    assert queue.qsize() == 0
    assert len(buffer.get_and_delete_of((client_id,), (message.type(),))) == 1


def test_unsubscribe_leaves_another_subscription_intact(communication_protocol: CommunicationProtocol) -> None:
    client_id_a = _make_client_id("client-1")
    client_id_b = _make_client_id("client-2")
    message_a = _make_message(msg_type=MessageType.SIMULATION_STEP)
    message_b = _make_message(msg_type=MessageType.CLIENT_META_DATA_REQUEST)
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)

    buffer.subscribe((client_id_a,), (message_a.type(),))
    queue_b = buffer.subscribe((client_id_b,), (message_b.type(),))

    buffer.unsubscribe((client_id_a,), (message_a.type(),))
    buffer.add(client_id_b, message_b)

    assert queue_b is not None
    assert queue_b.qsize() == 1


def test_get_and_delete_returns_and_removes_match(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)

    first = buffer.get_and_delete_of((client_id,), (message.type(),))

    assert len(first) == 1
    assert buffer.get_and_delete_of((client_id,), (message.type(),)) == []


def test_get_and_delete_ignores_non_matching(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id("client-1")
    other_client_id = _make_client_id("client-2")
    message = _make_message(msg_type=MessageType.SIMULATION_STEP)
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)

    result = buffer.get_and_delete_of((other_client_id,), (MessageType.CLIENT_META_DATA_REQUEST,))

    assert result == []
    assert len(buffer.get_and_delete_of((client_id,), (message.type(),))) == 1
