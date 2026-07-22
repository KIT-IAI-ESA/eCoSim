import pickle

from distributed import Client
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_event import ParallelEvent, ParallelEventDask, ParallelEventThread


def test_for_communication_protocol_builds_correct_type(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    match communication_protocol:
        case CommunicationProtocol.DASK:
            assert isinstance(event, ParallelEventDask)
        case CommunicationProtocol.TCP_SOCKET:
            assert isinstance(event, ParallelEventThread)


def test_for_communication_protocol_dask_uses_given_name() -> None:
    event = ParallelEvent.for_communication_protocol(CommunicationProtocol.DASK, dask_name="my_event")
    assert isinstance(event, ParallelEventDask)
    assert event._name == "my_event"  # noqa: SLF001


def test_dask_for_name_sets_name() -> None:
    event = ParallelEventDask.for_name("abc")
    assert event._name == "abc"  # noqa: SLF001


def test_set_then_is_set_true(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    event.set()
    assert event.is_set() is True


def test_set_then_clear_is_set_false(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    event.set()
    event.clear()
    assert event.is_set() is False


def test_is_set_false_by_default(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    assert event.is_set() is False


def test_wait_returns_true_when_set(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    event.set()
    assert event.wait(timeout=1.0) is True


def test_wait_returns_false_on_timeout(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    assert event.wait(timeout=0.01) is False


def test_set_state_true(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    event.set_state(True)
    assert event.is_set() is True


def test_set_state_false(
    communication_protocol: CommunicationProtocol,
) -> None:
    event = ParallelEvent.for_communication_protocol(communication_protocol)
    event.set()
    event.set_state(False)
    assert event.is_set() is False


def test_dask_reduce_roundtrip_preserves_name() -> None:
    event = ParallelEventDask.for_name("round_trip")
    restored = pickle.loads(pickle.dumps(event))
    assert isinstance(restored, ParallelEventDask)
    assert restored._name == "round_trip"  # noqa: SLF001


def test_dask_reduce_roundtrip_preserves_state(dask_client: Client) -> None:
    event = ParallelEventDask.for_name("round_trip")
    event.set()
    restored = pickle.loads(pickle.dumps(event))
    assert isinstance(restored, ParallelEventDask)
    assert restored._name == "round_trip"  # noqa: SLF001
    assert restored.is_set() is True
