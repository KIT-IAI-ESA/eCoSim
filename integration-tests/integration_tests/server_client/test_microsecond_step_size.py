import threading
from datetime import datetime

import pytest

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import generate_simple_test_server


def test_client_server_microsecond_step_size() -> None:
    """IT1: verify that a 25 µs step size is correctly transmitted from server to client
    and that the client accumulates the correct total simulated time."""
    server_host = "localhost"
    server_port = 47190
    step_size_in_us = 25
    steps = 4000
    simulation_start_date = datetime(year=2024, month=1, day=1)

    received_step_sizes: list[float] = []

    server = generate_simple_test_server(
        host=server_host,
        port=server_port,
        steps=steps,
        step_size_in_us=step_size_in_us,
        simulation_start_date=simulation_start_date,
    )
    client = SimpleTestClient.generate(
        server_host=server_host,
        server_port=server_port,
        on_simulation_step_return=lambda _self, received_inputs, step_secs: (
            received_step_sizes.append(step_secs)
            or ClientSimStepData(interface_values=[])
        ),
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    client.start()
    server_thread.join()

    expected_step_size_in_s = step_size_in_us / 1_000_000
    expected_total_s = steps * expected_step_size_in_s

    assert len(received_step_sizes) == steps, (
        f"Expected {steps} simulation steps, got {len(received_step_sizes)}"
    )
    assert all(s == expected_step_size_in_s for s in received_step_sizes), (
        f"Expected every step_size_in_seconds == {expected_step_size_in_s}, "
        f"got unique values: {set(received_step_sizes)}"
    )
    assert client.accumulated_step_sizes_in_seconds.value == pytest.approx(
        expected_total_s, abs=1e-9,
    ), (
        f"Expected accumulated time {expected_total_s} s, "
        f"got {client.accumulated_step_sizes_in_seconds.value} s"
    )
