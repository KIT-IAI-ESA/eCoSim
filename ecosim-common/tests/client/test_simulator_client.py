from unittest.mock import MagicMock

from ecosim_common.tech.shutdown_manager import ShutdownManager

from tests.client.spy_simulator_client import SpySimulatorClient


def test_initializes_the_model_only_once() -> None:
    client = SpySimulatorClient.create()

    client.on_simulation_start()
    client.on_simulation_start()

    assert client.calls == ["initialize at 0.0"]


def test_clears_the_model_only_once() -> None:
    client = SpySimulatorClient.create()

    client.on_app_shutdown()
    client.on_app_shutdown()

    assert client.calls == ["clear"]


def test_routes_list_inputs_to_the_matrix_setter_and_all_others_to_the_float_setter() -> None:
    client = SpySimulatorClient.create()

    client.on_simulation_step(received_inputs={"m": [1.0, 2.0], "f": 3.0, "n": None}, step_size_in_seconds=1.0)

    assert client.calls[:3] == ["matrix m=[1.0, 2.0]", "float f=3.0", "float n=None"]


def test_sets_every_input_before_the_step_and_advances_the_time_only_after_it() -> None:
    client = SpySimulatorClient.create()

    client.on_simulation_step(received_inputs={"a": 1.0, "b": 2.0}, step_size_in_seconds=0.5)
    client.on_simulation_step(received_inputs={"a": 3.0, "b": 4.0}, step_size_in_seconds=2.0)

    assert client.calls == ["float a=1.0", "float b=2.0", "step of 0.5 at 0.0", "float a=3.0", "float b=4.0", "step of 2.0 at 0.5"]
    assert client._current_simulation_time == 2.5  # noqa: SLF001


def test_a_shutdown_through_the_shutdown_manager_closes_the_channel_and_clears_once() -> None:
    channel = MagicMock()
    client = SpySimulatorClient.create(channel=channel)

    ShutdownManager().set_shutdown_at_application_end()

    channel.close.assert_called_once()
    assert client.calls == ["clear"]
