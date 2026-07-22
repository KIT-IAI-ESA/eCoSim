from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_list import ParallelList


def test_parallel_list(communication_protocol: CommunicationProtocol) -> None:
    list = ParallelList[str].for_communication_protocol(protocol=communication_protocol)
    list.append("hello")
    list.append("world")
    assert len(list) == 2
    assert list.snapshot()[0] == "hello"
    assert list.snapshot()[1] == "world"
