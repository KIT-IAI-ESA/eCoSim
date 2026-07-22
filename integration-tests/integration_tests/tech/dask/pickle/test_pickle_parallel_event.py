import pytest
from cloudpickle import cloudpickle
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


def test_pickle_parallel_event_dask() -> None:
    raw = cloudpickle.dumps(
        ParallelEvent.for_communication_protocol(
            CommunicationProtocol.DASK,
            dask_name="test_111",
        ),
    )
    unpickled = cloudpickle.loads(raw)
    assert unpickled._dask_event.name == "test_111"  # noqa: SLF001


def test_pickle_parallel_event_thread() -> None:
    with pytest.raises(TypeError):
        cloudpickle.dumps(
            ParallelEvent.for_communication_protocol(
                CommunicationProtocol.TCP_SOCKET,
                dask_name="test_111",
            ),
        )
