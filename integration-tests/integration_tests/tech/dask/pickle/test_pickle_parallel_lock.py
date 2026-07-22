import distributed
import pytest
from cloudpickle import cloudpickle
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock


def test_pickle_parallel_event_dask(dask_client: distributed.Client) -> None:
    raw = cloudpickle.dumps(
        ParallelLock.for_protocol(
            CommunicationProtocol.DASK,
            dask_name="test_111",
        ),
    )
    unpickled = cloudpickle.loads(raw)
    assert unpickled._lock.name == "test_111"  # noqa: SLF001


def test_pickle_parallel_event_thread() -> None:
    with pytest.raises(TypeError):
        cloudpickle.dumps(
            ParallelLock.for_protocol(
                CommunicationProtocol.TCP_SOCKET,
            ),
        )
