import pickle
from typing import List, Tuple

from distributed.protocol import register_serialization
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID

"""
# TODO SECURITY

The official pickle docs state (https://docs.python.org/3/library/pickle.html):

Warning

The pickle module is not secure. Only unpickle data you trust.

It is possible to construct malicious pickle data which will execute arbitrary code during unpickling. Never unpickle data that could have come from
an untrusted source, or that could have been tampered with.

Consider signing data with hmac if you need to ensure that it has not been tampered with.

Safer serialization formats such as json may be more appropriate if you are processing untrusted data. See Comparison with json.


-> so we need to clarify if we want to do it like this. Especially in co-simulations with different partners this might be a show stopper.
"""


def serialize_clientid(client_id: ClientID) -> Tuple[dict, List[bytes]]:
    return {}, [client_id.model_name.encode(), client_id.simulator_name.encode()]


def deserialize_clientid(header: dict, frames: List[bytes]) -> ClientID:
    return ClientID(frames[0].decode(), frames[1].decode())


def serialize_protocolinterfacevalue(protocol_interface_value: ProtocolInterfaceValue) -> Tuple[dict, List[bytes]]:
    return {}, [protocol_interface_value.name.encode(), pickle.dumps(protocol_interface_value.value)]


def deserialize_protocolinterfacevalue(header: dict, frames: List[bytes]) -> ProtocolInterfaceValue:
    return ProtocolInterfaceValue(frames[0].decode(), pickle.loads(frames[1]))


def serialize_classes() -> None:
    register_serialization(ClientID, serialize_clientid, deserialize_clientid)
    register_serialization(ProtocolInterfaceValue, serialize_protocolinterfacevalue, deserialize_protocolinterfacevalue)
