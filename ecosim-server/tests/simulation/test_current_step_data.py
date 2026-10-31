from datetime import datetime
from unittest.mock import Mock

from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import LogicalDelay, LogicalDelayConnection, SimulationConfig
from ecosim_server.simulation.current_step_data import CurrentStepData


def _connection(interface: str) -> LogicalDelayConnection:
    return LogicalDelayConnection(
        start_value=0.0,
        input_interface=SimulatorInterfaceId(
            simulator_name="sender",
            model_interface_id=ModelInterfaceId(model_name="sender", interface=interface),
        ),
        output_interface=SimulatorInterfaceId(
            simulator_name="receiver",
            model_interface_id=ModelInterfaceId(model_name="receiver", interface=interface),
        ),
    )


def _interfaces_by_delay(logical_delays: list[LogicalDelay]) -> dict[int, list[str]]:
    simulation_config = SimulationConfig(
        clients=[],
        steps=1,
        step_size_in_ms=1,
        start_date=datetime(year=2024, month=1, day=1),
        logical_delays=logical_delays,
    )
    current_step_data = CurrentStepData(server_config=Mock(spec=ServerConfig), simulation_config=simulation_config)
    delays = current_step_data.logical_delays_by_delay_step().get_snapshot()
    return {
        delay: [connection.output_interface.model_interface_id.interface for connection in logical_delay.connections]
        for delay, logical_delay in delays.items()
    }


def test_blocks_with_the_same_delay_keep_all_their_connections() -> None:
    interfaces_by_delay = _interfaces_by_delay(
        logical_delays=[
            LogicalDelay(delayed_time_steps=1, logical_delay_connections=[_connection("first")]),
            LogicalDelay(delayed_time_steps=1, logical_delay_connections=[_connection("second"), _connection("third")]),
        ],
    )

    assert interfaces_by_delay == {1: ["first", "second", "third"]}


def test_blocks_with_different_delays_stay_apart() -> None:
    interfaces_by_delay = _interfaces_by_delay(
        logical_delays=[
            LogicalDelay(delayed_time_steps=1, logical_delay_connections=[_connection("first")]),
            LogicalDelay(delayed_time_steps=2, logical_delay_connections=[_connection("second")]),
        ],
    )

    assert interfaces_by_delay == {1: ["first"], 2: ["second"]}
