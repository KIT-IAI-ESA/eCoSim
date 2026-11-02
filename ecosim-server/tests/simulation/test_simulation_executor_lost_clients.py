import pytest
from ecosim_common.communication.message_type import MessageType
from ecosim_server.simulation.simulation_executor import SimulationExecutor
from tests.simulation.simulation_executor_test_setup import (
    CLIENT_ID,
    SECOND_CLIENT_ID,
    answer_after,
    error_of_bounded_run,
    executor_with_client,
    executor_with_clients,
    fail_send,
    lose_connection,
)

_SHORT_TIMEOUT_IN_SECONDS = 0.1
_RESTORE_LIMIT_IN_SECONDS = 3.0
_GAP_BETWEEN_ANSWERS_IN_SECONDS = 2.0


@pytest.fixture
def short_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "_STEP_RESPONSE_TIMEOUT_IN_SECONDS",
        "_RESTORE_CONNECTION_CHECK_INTERVAL_IN_SECONDS",
    ):
        monkeypatch.setattr(SimulationExecutor, name, _SHORT_TIMEOUT_IN_SECONDS)


def _assert_names_the_client(error: Exception | None) -> None:
    assert isinstance(error, RuntimeError), error
    assert str(CLIENT_ID) in str(error)


@pytest.mark.usefixtures("short_timeouts")
def test_step_timeout_with_a_lost_client_fails_the_run() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP: lose_connection})

    _assert_names_the_client(error_of_bounded_run(executor))


@pytest.mark.usefixtures("short_timeouts")
def test_slow_client_is_waited_for_and_not_pinged() -> None:
    executor, fake_client = executor_with_client(reactions={MessageType.SIMULATION_STEP: answer_after(_SHORT_TIMEOUT_IN_SECONDS * 5)})

    assert error_of_bounded_run(executor) is None
    assert MessageType.SIMULATION_STEP in fake_client.answered_types
    assert MessageType.PING not in fake_client.received_types


def test_failed_step_send_fails_the_run_without_waiting_for_the_timeout() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP: fail_send})

    error = error_of_bounded_run(executor)

    _assert_names_the_client(error)
    assert "broken pipe" in str(error)


def test_client_lost_during_start_up_names_it() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_START: lose_connection})

    _assert_names_the_client(error_of_bounded_run(executor))


@pytest.mark.usefixtures("short_timeouts")
def test_restore_with_a_lost_client_fails_before_the_restore_timeout() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP_BATCH: lose_connection}, restore=True)

    _assert_names_the_client(error_of_bounded_run(executor))


def test_failed_restore_send_fails_the_run_without_waiting_for_the_timeout() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP_BATCH: fail_send}, restore=True)

    error = error_of_bounded_run(executor)

    _assert_names_the_client(error)
    assert "broken pipe" in str(error)


@pytest.mark.usefixtures("short_timeouts")
def test_slow_restore_of_a_connected_client_is_waited_for() -> None:
    executor, fake_client = executor_with_client(
        reactions={MessageType.SIMULATION_STEP_BATCH: answer_after(_SHORT_TIMEOUT_IN_SECONDS * 5)},
        restore=True,
    )

    assert error_of_bounded_run(executor) is None
    assert MessageType.SIMULATION_STEP_BATCH in fake_client.answered_types


@pytest.mark.usefixtures("short_timeouts")
def test_restore_of_a_connected_client_still_ends_at_the_restore_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SimulationExecutor, "_RESTORE_RESPONSE_TIMEOUT_IN_SECONDS", _SHORT_TIMEOUT_IN_SECONDS * 3)
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP_BATCH: lambda _client, _message: None}, restore=True)

    error = error_of_bounded_run(executor)

    assert isinstance(error, RuntimeError)
    assert "Timeout" in str(error)


@pytest.mark.usefixtures("short_timeouts")
def test_restore_limit_restarts_after_each_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both gaps between the answers are under the limit, while the total is over it."""
    monkeypatch.setattr(SimulationExecutor, "_RESTORE_RESPONSE_TIMEOUT_IN_SECONDS", _RESTORE_LIMIT_IN_SECONDS)
    executor, fake_clients = executor_with_clients(
        reactions_by_client={
            CLIENT_ID: {MessageType.SIMULATION_STEP_BATCH: answer_after(_GAP_BETWEEN_ANSWERS_IN_SECONDS)},
            SECOND_CLIENT_ID: {MessageType.SIMULATION_STEP_BATCH: answer_after(_GAP_BETWEEN_ANSWERS_IN_SECONDS * 2)},
        },
        restore=True,
    )

    assert error_of_bounded_run(executor) is None
    assert all(MessageType.SIMULATION_STEP_BATCH in fake_client.answered_types for fake_client in fake_clients)
