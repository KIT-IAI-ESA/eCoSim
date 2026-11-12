from pathlib import Path
from typing import List

import pytest
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_test_common.test_data.generate_simulation_file import a_logical_delay, a_simulator, an_input, an_output, config_file
from tests.data.generate_connection_config import single_delay_file
from tests.simulation.logical_delay_test_setup import run_simulation


def _sent_number(step: int) -> dict[InterfaceId, InterfaceValue]:
    return {"sent": 100.0 + step}


def _sent_list(step: int) -> dict[InterfaceId, InterfaceValue]:
    return {"sent": [100.0 + step, 200.0 + step]}


def _received_numbers(directory: Path, delay: int, steps: int) -> List[InterfaceValue]:
    clients = run_simulation(
        simulation_file=single_delay_file(directory=directory, delay=delay, start_value="-1.0"),
        steps=steps,
        outputs_by_simulator={"sender": _sent_number},
    )
    return clients["receiver"].received_inputs("delayed")


def test_delay_of_one_arrives_one_step_later(tmp_path: Path) -> None:
    assert _received_numbers(directory=tmp_path, delay=1, steps=5) == [-1.0, 100.0, 101.0, 102.0, 103.0]


def test_delay_of_two_arrives_two_steps_later(tmp_path: Path) -> None:
    assert _received_numbers(directory=tmp_path, delay=2, steps=6) == [-1.0, -1.0, 100.0, 101.0, 102.0, 103.0]


def test_delay_of_three_arrives_three_steps_later(tmp_path: Path) -> None:
    assert _received_numbers(directory=tmp_path, delay=3, steps=6) == [-1.0, -1.0, -1.0, 100.0, 101.0, 102.0]


@pytest.mark.parametrize(
    ("delay", "skipped_steps", "expected"),
    [
        pytest.param(2, (2, 3), [-1.0, -1.0, 100.0, 101.0, 101.0, 101.0, 104.0, 105.0, 106.0], id="delay 2"),
        pytest.param(3, (1, 2, 3, 4), [-1.0, -1.0, -1.0, 100.0, 100.0, 100.0, 100.0, 100.0, 105.0], id="gap longer than the delay"),
    ],
)
def test_step_that_sends_nothing_holds_the_last_value(
    tmp_path: Path,
    delay: int,
    skipped_steps: tuple[int, ...],
    expected: List[InterfaceValue],
) -> None:
    clients = run_simulation(
        simulation_file=single_delay_file(directory=tmp_path, delay=delay, start_value="-1.0"),
        steps=9,
        outputs_by_simulator={"sender": lambda step: {} if step in skipped_steps else _sent_number(step)},
    )

    assert clients["receiver"].received_inputs("delayed") == expected


def test_list_start_value_arrives_until_the_first_delayed_list(tmp_path: Path) -> None:
    clients = run_simulation(
        simulation_file=single_delay_file(directory=tmp_path, delay=2, start_value=[1.0, "2.5"]),
        steps=4,
        outputs_by_simulator={"sender": _sent_list},
    )

    assert clients["receiver"].received_inputs("delayed") == [[1.0, 2.5], [1.0, 2.5], [100.0, 200.0], [101.0, 201.0]]


def test_blocks_with_different_delays_keep_their_own_values(tmp_path: Path) -> None:
    file = config_file(
        tmp_path,
        a_simulator("sender", an_output("sent")),
        a_simulator(
            "receiver",
            an_input("short", simulator="0", interface="sent", delay_path=["1"]),
            an_input("long", simulator="0", interface="sent", delay_path=["2"]),
            an_input("short_too", simulator="0", interface="sent", delay_path=["3"]),
        ),
        logical_delays=[
            a_logical_delay("receiver", "short", delay=1, start_value="-1"),
            a_logical_delay("receiver", "long", delay=3, start_value="-3"),
            a_logical_delay("receiver", "short_too", delay=1, start_value="-2"),
        ],
    )

    clients = run_simulation(simulation_file=file, steps=5, outputs_by_simulator={"sender": _sent_number})

    assert clients["receiver"].received_inputs("short") == [-1.0, 100.0, 101.0, 102.0, 103.0]
    assert clients["receiver"].received_inputs("long") == [-3.0, -3.0, -3.0, 100.0, 101.0]
    assert clients["receiver"].received_inputs("short_too") == [-2.0, 100.0, 101.0, 102.0, 103.0]


def test_delay_counts_steps_when_the_sender_runs_after_the_receiver(tmp_path: Path) -> None:
    """'fed_back' makes the sender wait for the 'answer' of the receiver, so the receiver runs first in every step."""
    file = config_file(
        tmp_path,
        a_simulator("sender", an_output("sent"), an_input("fed_back", simulator="1", interface="answer")),
        a_simulator("receiver", an_output("answer"), an_input("delayed", simulator="0", interface="sent", delay_path=["1"])),
        logical_delays=[a_logical_delay("receiver", "delayed", delay=2, start_value="-1")],
    )

    clients = run_simulation(
        simulation_file=file,
        steps=5,
        outputs_by_simulator={"sender": _sent_number, "receiver": lambda step: {"answer": 500.0 + step}},
    )

    assert clients["sender"].received_inputs("fed_back") == [500.0, 501.0, 502.0, 503.0, 504.0]
    assert clients["receiver"].received_inputs("delayed") == [-1.0, -1.0, 100.0, 101.0, 102.0]
