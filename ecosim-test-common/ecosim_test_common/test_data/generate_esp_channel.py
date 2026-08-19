from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol


def generate_esp_channel(
    communication_protocol: CommunicationProtocol,
) -> ESPChannel:
    return ESPChannel.for_protocol(
        communication_protocol=communication_protocol,
        connection_address=ConnectionAddress("localhost", 33471),
        dask_id="TEST_DASK_ID",
    )
