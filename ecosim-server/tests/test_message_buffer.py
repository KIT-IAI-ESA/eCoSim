from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.structures.esp_set import ESPSet
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.message_buffer import BufferedClientMessage, ClientMessageBuffer


def _make_message(msg_type: MessageType = MessageType.SIMULATION_STEP, correlation_id: int = 1, payload: str = "payload-1") -> ESPChannelMessage:
    return ESPChannelMessageJson(
        _type=msg_type,
        _correlation_id=CorrelationId.of_int(correlation_id),
        _payload=payload,
    )


def _make_client_id(model: str = "model") -> ClientID:
    return ClientID(model_name=model, simulator_name="simulator")


def test_add_no_callback_appends_to_buffer(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)
    result = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert len(result) == 1
    assert result[0].client_id == client_id


def test_add_with_matching_callback_skips_buffer(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.on_message((client_id,), (message.type(),), lambda m: None)
    buffer.add(client_id, message)
    result = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert result == []


def test_on_message_registers_and_consumes_future_message(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.on_message((client_id,), (message.type(),), lambda m: None)
    buffer.add(client_id, message)
    result = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert result == []


def test_on_message_drains_pre_existing_buffered_messages(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)
    buffer.on_message((client_id,), (message.type(),), lambda m: None)
    result = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert result == []


def test_on_message_executes_callback_on_matching_message(
    communication_protocol: CommunicationProtocol,
) -> None:
    client_id = _make_client_id()
    message = _make_message()
    received: ESPSet[BufferedClientMessage] = ESPSet.of_type(
        set_type=(ESPStructureType.THREAD if communication_protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK),
    )
    done = ParallelEvent.for_communication_protocol(communication_protocol)

    def callback(m: BufferedClientMessage) -> None:
        received.add(m)
        done.set()

    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.on_message((client_id,), (message.type(),), callback)
    buffer.add(client_id, message)

    assert done.wait(), "callback was not executed within timeout"
    assert len(received) == 1


def test_remove_callback_then_message_is_buffered(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.on_message((client_id,), (message.type(),), lambda m: None)
    buffer.remove_on_message_callback((client_id,), (message.type(),))
    buffer.add(client_id, message)
    result = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert len(result) == 1


def test_remove_callback_leaves_other_callback_intact(communication_protocol: CommunicationProtocol) -> None:
    client_id_a = _make_client_id("client-1")
    client_id_b = _make_client_id("client-2")
    message_a = _make_message(msg_type=MessageType.SIMULATION_STEP)
    message_b = _make_message(msg_type=MessageType.CLIENT_META_DATA_REQUEST)
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.on_message((client_id_a,), (message_a.type(),), lambda m: None)
    buffer.on_message((client_id_b,), (message_b.type(),), lambda m: None)
    buffer.remove_on_message_callback((client_id_a,), (message_a.type(),))
    buffer.add(client_id_b, message_b)
    result = buffer.get_and_delete_of((client_id_b,), (message_b.type(),))
    assert result == []


def test_get_and_delete_returns_and_removes_match(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id()
    message = _make_message()
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)
    first = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert len(first) == 1
    second = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert second == []


def test_get_and_delete_ignores_non_matching(communication_protocol: CommunicationProtocol) -> None:
    client_id = _make_client_id("client-1")
    other_client_id = _make_client_id("client-2")
    message = _make_message(msg_type=MessageType.SIMULATION_STEP)
    buffer = ClientMessageBuffer.for_communication_protocol(communication_protocol)
    buffer.add(client_id, message)
    result = buffer.get_and_delete_of((other_client_id,), (MessageType.CLIENT_META_DATA_REQUEST,))
    assert result == []
    remaining = buffer.get_and_delete_of((client_id,), (message.type(),))
    assert len(remaining) == 1
