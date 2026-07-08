from distributed.protocol import register_serialization
from typing import Tuple, List
import pickle

from ecosim_common.config.client_id import ClientID
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.simulation.current_step_data import CurrentStepData
from ecosim_server.server_state import ServerStateDask

'''
# TODO SECURITY

The official pickle docs state (https://docs.python.org/3/library/pickle.html):

Warning

The pickle module is not secure. Only unpickle data you trust.

It is possible to construct malicious pickle data which will execute arbitrary code during unpickling. Never unpickle data that could have come from
an untrusted source, or that could have been tampered with.

Consider signing data with hmac if you need to ensure that it has not been tampered with.

Safer serialization formats such as json may be more appropriate if you are processing untrusted data. See Comparison with json.


-> so we need to clarify if we want to do it like this. Especially in co-simulations with different partners this might be a show stopper.
'''


def serialize_clientid(client_id: ClientID) -> Tuple[dict, List[bytes]]:
    return {}, [client_id.model_name.encode(), client_id.simulator_name.encode()]


def deserialize_clientid(header: dict, frames: List[bytes]) -> ClientID:
    return ClientID(frames[0].decode(), frames[1].decode())


def serialize_protocolinterfacevalue(protocol_interface_value: ProtocolInterfaceValue) -> Tuple[dict, List[bytes]]:
    return {}, [protocol_interface_value.name.encode(), pickle.dumps(protocol_interface_value.value)]


def deserialize_protocolinterfacevalue(header: dict, frames: List[bytes]) -> ProtocolInterfaceValue:
    return ProtocolInterfaceValue(frames[0].decode(), pickle.loads(frames[1]))


def serialize_serverstate(server_state: ServerStateDask) -> Tuple[dict, List[bytes]]:
    return {}, [pickle.dumps(server_state)]


def deserialize_serverstate(header: dict, frames: List[bytes]) -> ServerStateDask:
    return pickle.loads(frames[0])


def serialize_currentstepdata(current_step_data: CurrentStepData) -> Tuple[dict, List[bytes]]:
    return {}, [pickle.dumps(current_step_data)]


def deserialize_currentstepdata(header: dict, frames: List[bytes]) -> CurrentStepData:
    return pickle.loads(frames[0])


def serialize_classes() -> None:
    register_serialization(ClientID, serialize_clientid, deserialize_clientid)
    register_serialization(ProtocolInterfaceValue, serialize_protocolinterfacevalue, deserialize_protocolinterfacevalue)
    register_serialization(ServerStateDask, serialize_serverstate, deserialize_serverstate)
    register_serialization(CurrentStepData, serialize_currentstepdata, deserialize_currentstepdata)
