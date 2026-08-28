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
    # after unpickling, the lock should be None
    assert unpickled._dask_lock is None  # noqa: SLF001
    assert unpickled._name == "test_111"  # noqa: SLF001
    # after acquiring it the first time after unpickling, the lock should be available
    with unpickled:
        assert unpickled._dask_lock is not None  # noqa: SLF001
        assert unpickled._dask_lock.name == "test_111"  # noqa: SLF001
        assert unpickled._name == "test_111"  # noqa: SLF001


def test_pickle_parallel_event_thread() -> None:
    with pytest.raises(TypeError):
        cloudpickle.dumps(
            ParallelLock.for_protocol(
                CommunicationProtocol.TCP_SOCKET,
            ),
        )
