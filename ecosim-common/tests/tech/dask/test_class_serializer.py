from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.dask.class_serializer import (
    deserialize_clientid,
    deserialize_protocolinterfacevalue,
    serialize_clientid,
    serialize_protocolinterfacevalue,
)


def test_a_client_id_is_deserialized_from_memoryview_frames() -> None:
    """Dask passes received frames as memoryviews, e.g. for the arguments of an actor call."""
    header, frames = serialize_clientid(ClientID(model_name="model", simulator_name="simulator"))

    client_id = deserialize_clientid(header, [memoryview(frame) for frame in frames])

    assert client_id == ClientID(model_name="model", simulator_name="simulator")


def test_a_protocol_interface_value_is_deserialized_from_memoryview_frames() -> None:
    header, frames = serialize_protocolinterfacevalue(ProtocolInterfaceValue(name="temperature", value=[1.5, 2.5]))

    value = deserialize_protocolinterfacevalue(header, [memoryview(frame) for frame in frames])

    assert value == ProtocolInterfaceValue(name="temperature", value=[1.5, 2.5])
