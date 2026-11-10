from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.simulation.response_timeouts import ResponseTimeouts
from ecosim_test_common.timeouts import SHORT_TIMEOUT_IN_SECONDS
from tests.simulation.simulation_executor_test_setup import (
    CLIENT_ID,
    answer_after,
    error_of_bounded_run,
    executor_with_client,
    executor_with_clients,
    lose_connection,
)

_SHORT_TIMEOUTS = ResponseTimeouts(
    step_response_timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
    restore_connection_check_interval_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
)


def _assert_names_the_client(error: Exception | None) -> None:
    assert isinstance(error, RuntimeError), error
    assert str(CLIENT_ID) in str(error)


def test_step_timeout_with_a_lost_client_fails_the_run() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP: lose_connection}, response_timeouts=_SHORT_TIMEOUTS)

    _assert_names_the_client(error_of_bounded_run(executor))


def test_slow_client_does_not_fail_the_run() -> None:
    executor, _ = executor_with_client(
        reactions={MessageType.SIMULATION_STEP: answer_after(delay_in_seconds=SHORT_TIMEOUT_IN_SECONDS * 1.5)},
        response_timeouts=_SHORT_TIMEOUTS,
    )

    assert error_of_bounded_run(executor) is None


def test_client_lost_during_start_up_names_it() -> None:
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_START: lose_connection})

    _assert_names_the_client(error_of_bounded_run(executor))


def test_client_lost_during_restore_fails_the_run() -> None:
    executor, _ = executor_with_client(
        reactions={MessageType.SIMULATION_STEP_BATCH: lose_connection},
        restore=True,
        response_timeouts=_SHORT_TIMEOUTS,
    )

    _assert_names_the_client(error_of_bounded_run(executor))


def test_slow_restore_of_a_connected_client_is_waited_for() -> None:
    executor, fake_client = executor_with_client(
        reactions={MessageType.SIMULATION_STEP_BATCH: answer_after(delay_in_seconds=SHORT_TIMEOUT_IN_SECONDS * 1.5)},
        restore=True,
        response_timeouts=_SHORT_TIMEOUTS,
    )

    assert error_of_bounded_run(executor) is None
    # step 0 is restored, so the run continues with step 1
    assert fake_client.received_steps() == [1]


def test_restore_of_a_connected_client_still_ends_at_the_restore_timeout() -> None:
    executor, _ = executor_with_client(
        reactions={MessageType.SIMULATION_STEP_BATCH: lambda _client, _message: None},
        restore=True,
        response_timeouts=ResponseTimeouts(
            restore_response_timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS * 3,
            restore_connection_check_interval_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
        ),
    )

    error = error_of_bounded_run(executor)

    assert isinstance(error, RuntimeError)
    assert "Timeout" in str(error)


def test_restore_timeout_restarts_after_each_response() -> None:
    """Both gaps between the answers are under the timeout, while the total is over it."""
    restore_timeout_in_seconds = 3.0
    gap_between_answers_in_seconds = 2.0
    second_client_id = ClientID(model_name="second_model", simulator_name="simulator")
    executor, _ = executor_with_clients(
        reactions_by_client={
            CLIENT_ID: {MessageType.SIMULATION_STEP_BATCH: answer_after(delay_in_seconds=gap_between_answers_in_seconds)},
            second_client_id: {MessageType.SIMULATION_STEP_BATCH: answer_after(delay_in_seconds=gap_between_answers_in_seconds * 2)},
        },
        restore=True,
        response_timeouts=ResponseTimeouts(
            restore_response_timeout_in_seconds=restore_timeout_in_seconds,
            restore_connection_check_interval_in_seconds=SHORT_TIMEOUT_IN_SECONDS,
        ),
    )

    assert error_of_bounded_run(executor) is None
