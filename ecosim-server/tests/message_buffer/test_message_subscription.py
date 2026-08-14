import time
from typing import List

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_message import ClientMessage
from ecosim_server.client.client_message_buffer import ClientMessageBuffer
from ecosim_server.client.message_subscription import MessageSubscription

_MESSAGE_TYPE = MessageType.SIMULATION_START
_CLIENT_ID_1 = ClientID(model_name="model-1", simulator_name="simulator")
_CLIENT_ID_2 = ClientID(model_name="model-2", simulator_name="simulator")


def _make_message(correlation_id: int = 1) -> ESPChannelMessage:
    return ESPChannelMessageJson(
        _type=_MESSAGE_TYPE,
        _correlation_id=CorrelationId.of_int(correlation_id),
        _payload="payload",
    )


def _open_subscription(
    message_buffer: ClientMessageBuffer,
) -> MessageSubscription:
    return MessageSubscription.open(
        message_buffer=message_buffer,
        client_ids=(_CLIENT_ID_1, _CLIENT_ID_2),
        message_types=(_MESSAGE_TYPE,),
    )


def _collect(
    subscription: MessageSubscription,
    expected_count: int,
    timeout_in_seconds: float = 10,
) -> List[ClientMessage]:
    messages: List[ClientMessage] = []
    while len(messages) < expected_count:
        message = subscription.next_message(timeout_in_seconds=timeout_in_seconds)
        if message is None:
            break
        messages.append(message)
    return messages


def _wait_until_queued(
    subscription: MessageSubscription,
    expected_count: int,
    timeout_in_seconds: float = 10,
) -> None:
    deadline = time.monotonic() + timeout_in_seconds
    while subscription.pending_message_count() < expected_count and time.monotonic() < deadline:
        time.sleep(0.01)
    assert subscription.pending_message_count() == expected_count


def test_next_message_returns_a_message_that_arrived_before_the_wait(communication_protocol: CommunicationProtocol) -> None:
    message_buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    with _open_subscription(message_buffer) as subscription:
        message_buffer.add(_CLIENT_ID_1, _make_message())

        assert subscription.next_message(timeout_in_seconds=10) is not None


def test_next_message_returns_none_on_timeout(communication_protocol: CommunicationProtocol) -> None:
    message_buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    with _open_subscription(message_buffer) as subscription:
        assert subscription.next_message(timeout_in_seconds=0.2) is None


def test_messages_arriving_between_two_waits_are_not_lost(communication_protocol: CommunicationProtocol) -> None:
    """
    Messages are delivered by the thread that received them, so one can arrive while the caller is not waiting.

    A caller that opens and closes its subscription around every single wait loses exactly those messages -
    that is why a subscription has to stay open for the whole waiting phase.
    """
    message_buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    with _open_subscription(message_buffer) as subscription:
        message_buffer.add(_CLIENT_ID_1, _make_message(correlation_id=1))
        message_buffer.add(_CLIENT_ID_2, _make_message(correlation_id=2))

        received = _collect(subscription, expected_count=2)

    assert {message.client_id for message in received} == {_CLIENT_ID_1, _CLIENT_ID_2}


def test_pending_messages_returns_everything_queued_so_far(communication_protocol: CommunicationProtocol) -> None:
    message_buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    with _open_subscription(message_buffer) as subscription:
        message_buffer.add(_CLIENT_ID_1, _make_message())
        assert subscription.next_message(timeout_in_seconds=10) is not None

        assert subscription.pending_messages() == []


def test_close_hands_unconsumed_messages_back_to_the_buffer(communication_protocol: CommunicationProtocol) -> None:
    message_buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    subscription = _open_subscription(message_buffer)
    message_buffer.add(_CLIENT_ID_1, _make_message())
    _wait_until_queued(subscription, expected_count=1)

    subscription.close()

    assert len(message_buffer.get_and_delete_of((_CLIENT_ID_1,), (_MESSAGE_TYPE,))) == 1


def test_close_stops_the_delivery_into_the_subscription(communication_protocol: CommunicationProtocol) -> None:
    message_buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    subscription = _open_subscription(message_buffer)
    subscription.close()

    message_buffer.add(_CLIENT_ID_1, _make_message())

    assert len(message_buffer.get_and_delete_of((_CLIENT_ID_1,), (_MESSAGE_TYPE,))) == 1
