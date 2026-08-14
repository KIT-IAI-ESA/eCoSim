import dask.distributed as dd
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_message_buffer import ClientMessageBuffer
from ecosim_server.client.message_subscription import MessageSubscription

_CLIENT_ID = ClientID(model_name="model", simulator_name="simulator")
_MESSAGE_TYPE = MessageType.SIMULATION_STEP


def test_message_added_on_a_worker_reaches_the_subscription_here(dask_client: dd.Client) -> None:
    message_buffer = ClientMessageBuffer.for_communication_protocol(CommunicationProtocol.DASK)
    message = ESPChannelMessageJson(
        _type=_MESSAGE_TYPE,
        _correlation_id=CorrelationId.of_int(7),
        _payload="payload",
    )
    with MessageSubscription.open(
        message_buffer=message_buffer,
        client_ids=(_CLIENT_ID,),
        message_types=(_MESSAGE_TYPE,),
    ) as subscription:
        dask_client.submit(message_buffer.add, _CLIENT_ID, message).result(timeout=30)

        received = subscription.next_message(timeout_in_seconds=30)

    assert received is not None
    assert received.client_id == _CLIENT_ID
    assert received.message.correlation_id() == CorrelationId.of_int(7)
