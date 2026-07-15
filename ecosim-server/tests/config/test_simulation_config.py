from datetime import datetime, timezone

from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ConnectedToData

from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import SimulationConfig
from tests.tech.resource_utils import resource_path_file


def test_load() -> None:
    config: SimulationConfig = SimulationConfig.of_config_file_and_params(resource_path_file("simulation.json"), 1221)

    assert config.step_size_in_ms == 60000
    assert config.steps == 1221
    assert config.start_date == datetime(year=2024, month=3, day=17, hour=13, minute=59, second=7, microsecond=123000, tzinfo=timezone.utc)
    assert config.pace == 1.0

    # CLIENTS
    assert len(config.clients) == 4

    # CLIENTS[0]
    client0 = config.clients[0]
    assert client0.simulator_name == "weather"
    assert client0.model_name == "weather"
    assert len(client0.interfaces) == 2
    # CLIENTS[0].INTERFACE[0]
    interface0 = client0.interfaces[0]
    assert interface0.model_interface_id == ModelInterfaceId(model_name="weather", interface="T_out")
    assert interface0.name == "T_out"
    assert interface0.type == InterfaceType.OUTPUT
    assert interface0.unit == "K"
    assert interface0.required is False
    assert interface0.description == ""
    assert len(interface0.connected_to) == 0
    # CLIENTS[0].INTERFACE[1]
    interface1 = client0.interfaces[1]
    assert interface1.model_interface_id == ModelInterfaceId(model_name="weather", interface="dir_sol_irradiance")
    assert interface1.name == "dir_sol_irradiance"
    assert interface1.type == InterfaceType.OUTPUT
    assert interface1.unit == "W/m2"
    assert interface1.required is False
    assert interface1.description == ""
    assert len(interface1.connected_to) == 0

    # CLIENTS[1]
    client1 = config.clients[1]
    assert client1.simulator_name == "house"
    assert client1.model_name == "house"
    assert len(client1.interfaces) == 6
    # CLIENTS[1].INTERFACE[0]
    interface0 = client1.interfaces[0]
    assert interface0.model_interface_id == ModelInterfaceId("house", "T_out")
    assert interface0.name == "T_out"
    assert interface0.type == InterfaceType.INPUT
    assert interface0.unit == ""
    assert interface0.required is True
    assert interface0.description == ""
    assert interface0.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId("weather", ModelInterfaceId("weather", "T_out")),
            delay_path=[],
        ),
    ]
    # CLIENTS[1].INTERFACE[1]
    interface1 = client1.interfaces[1]
    assert interface1.model_interface_id == ModelInterfaceId("house", "ventilation_pressure_control_signal")
    assert interface1.name, "ventilation_pressure_control_signal"
    assert interface1.type == InterfaceType.INPUT
    assert interface1.unit == ""
    assert interface1.required is True
    assert interface1.description == ""
    assert interface1.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId(
                "ventilation",
                ModelInterfaceId(
                    "ventilation",
                    "ventilation_pressure_control_signal",
                ),
            ),
            delay_path=[],
        ),
    ]
    # CLIENTS[1].INTERFACE[2]
    interface2 = client1.interfaces[2]
    assert interface2.model_interface_id == ModelInterfaceId("house", "heating_heatExchanger_control_signal")
    assert interface2.name == "heating_heatExchanger_control_signal"
    assert interface2.type == InterfaceType.INPUT
    assert interface2.unit == ""
    assert interface2.required is True
    assert interface2.description == ""
    assert interface2.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId("heating", ModelInterfaceId("heating", "heating_control_signal")),
            delay_path=[],
        ),
    ]
    # CLIENTS[1].INTERFACE[3]
    interface3 = client1.interfaces[3]
    assert interface3.model_interface_id == ModelInterfaceId("house", "vetnilation_valve_control_signal")
    assert interface3.name == "vetnilation_valve_control_signal"
    assert interface3.type == InterfaceType.INPUT
    assert interface3.unit == ""
    assert interface3.required is True
    assert interface3.description == ""
    assert interface3.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId(
                "ventilation",
                ModelInterfaceId(
                    "ventilation",
                    "ventilation_valve_control_signal",
                ),
            ),
            delay_path=[],
        ),
    ]
    # CLIENTS[1].INTERFACE[4]
    interface4 = client1.interfaces[4]
    assert interface4.model_interface_id == ModelInterfaceId("house", "dir_sol_iradiance")
    assert interface4.name == "dir_sol_iradiance"
    assert interface4.type == InterfaceType.INPUT
    assert interface4.unit == ""
    assert interface4.required is True
    assert interface4.description == "direct solar iradiance"
    assert interface4.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId(
                "weather",
                ModelInterfaceId(
                    "weather",
                    "dir_sol_irradiance",
                ),
            ),
            delay_path=[],
        ),
    ]
    # CLIENTS[1].INTERFACE[5]
    interface5 = client1.interfaces[5]
    assert interface5.model_interface_id == ModelInterfaceId("house", "room_temperature")
    assert interface5.name == "room_temperature"
    assert interface5.type == InterfaceType.OUTPUT
    assert interface5.unit == ""
    assert interface5.required is False
    assert interface5.description == ""
    assert len(interface5.connected_to) == 0

    # CLIENTS[2].INTERFACE[0]
    client2 = config.clients[2]
    interface0 = client2.interfaces[0]
    assert interface0.model_interface_id == ModelInterfaceId("heating", "T_room")
    assert interface0.name == "T_room"
    assert interface0.type == InterfaceType.INPUT
    assert interface0.unit == ""
    assert interface0.required is True
    assert interface0.description == "T_room"
    assert interface0.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId("house", ModelInterfaceId("house", "room_temperature")),
            delay_path=["1"],
        ),
    ]

    # CLIENTS[2].INTERFACE[1]
    interface1 = client2.interfaces[1]
    assert interface1.model_interface_id == ModelInterfaceId("heating", "heating_control_signal")
    assert interface1.name == "heating_control_signal"
    assert interface1.type == InterfaceType.OUTPUT
    assert interface1.unit == ""
    assert interface1.required is False
    assert interface1.description == "heating_control_signal"
    assert interface1.connected_to == []

    # CLIENTS[3].INTERFACE[0]
    client3 = config.clients[3]
    interface0 = client3.interfaces[0]
    assert interface0.model_interface_id == ModelInterfaceId("ventilation", "T_room")
    assert interface0.name == "T_room"
    assert interface0.type == InterfaceType.INPUT
    assert interface0.unit == ""
    assert interface0.required is True
    assert interface0.description == "T_room"
    assert interface0.connected_to == [
        ConnectedToData(
            simulator_interface_id=SimulatorInterfaceId("house", ModelInterfaceId("house", "room_temperature")),
            delay_path=["1"],
        ),
    ]

    # CLIENTS[3].INTERFACE[1]
    interface1 = client3.interfaces[1]
    assert interface1.model_interface_id == ModelInterfaceId("ventilation", "ventilation_pressure_control_signal")
    assert interface1.name == "ventilation_pressure_control_signal"
    assert interface1.type == InterfaceType.OUTPUT
    assert interface1.unit == ""
    assert interface1.required is False
    assert interface1.description == "ventilation_pressure_control_signal"
    assert interface1.connected_to == []

    # CLIENTS[3].INTERFACE[2]
    interface2 = client3.interfaces[2]
    assert interface2.model_interface_id == ModelInterfaceId("ventilation", "ventilation_valve_control_signal")
    assert interface2.name == "ventilation_valve_control_signal"
    assert interface2.type == InterfaceType.OUTPUT
    assert interface2.unit == ""
    assert interface2.required is False
    assert interface2.description == "ventilation_valve_control_signal"
    assert interface2.connected_to == []

    # LOGICAL DELAYS
    assert len(config.logical_delays) == 1
    assert config.logical_delays[0].delayed_time_steps == 1
    assert len(config.logical_delays[0].logical_delay_connections) == 2
    # LOGICAL_DELAY.INTERFACE[0]
    assert config.logical_delays[0].logical_delay_connections[0].start_value == 20.0
    assert config.logical_delays[0].logical_delay_connections[0].output_interface == SimulatorInterfaceId(
        simulator_name="heating",
        model_interface_id=ModelInterfaceId(
            model_name="heating",
            interface="T_room",
        ),
    )
    assert config.logical_delays[0].logical_delay_connections[0].input_interface == SimulatorInterfaceId(
        simulator_name="house",
        model_interface_id=ModelInterfaceId(
            model_name="house",
            interface="room_temperature",
        ),
    )
    # LOGICAL_DELAY.INTERFACE[1]
    assert config.logical_delays[0].logical_delay_connections[1].start_value == 20.0
    assert config.logical_delays[0].logical_delay_connections[1].output_interface == SimulatorInterfaceId(
        simulator_name="ventilation",
        model_interface_id=ModelInterfaceId(
            model_name="ventilation",
            interface="T_room",
        ),
    )
    assert config.logical_delays[0].logical_delay_connections[1].input_interface == SimulatorInterfaceId(
        simulator_name="house",
        model_interface_id=ModelInterfaceId(
            model_name="house",
            interface="room_temperature",
        ),
    )


def test_without_start_date() -> None:
    config = SimulationConfig.of_config_file_and_params(resource_path_file("simulation_without_start_date.json"), 1221)

    assert config.step_size_in_ms == 60000
    assert config.steps == 1221
    assert config.start_date == datetime(year=2024, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def test_date_time_for_step() -> None:
    config = SimulationConfig.of_config_file_and_params(resource_path_file("simulation.json"), 1221)
    assert config.step_size_in_ms == 60000
    assert config.start_date == datetime(year=2024, month=3, day=17, hour=13, minute=59, second=7, microsecond=123000, tzinfo=timezone.utc)

    step_1 = config.date_time_for_step(1)
    step_10 = config.date_time_for_step(10)
    step_777 = config.date_time_for_step(777)

    assert step_1 == datetime(year=2024, month=3, day=17, hour=14, minute=1, second=7, microsecond=123000, tzinfo=timezone.utc)
    assert step_10 == datetime(year=2024, month=3, day=17, hour=14, minute=10, second=7, microsecond=123000, tzinfo=timezone.utc)
    assert step_777 == datetime(year=2024, month=3, day=18, hour=2, minute=57, second=7, microsecond=123000, tzinfo=timezone.utc)


def test_date_time_to_step() -> None:
    config = SimulationConfig.of_config_file_and_params(resource_path_file("simulation.json"), 1221)
    assert config.step_size_in_ms == 60000
    assert config.start_date == datetime(year=2024, month=3, day=17, hour=13, minute=59, second=7, microsecond=123000, tzinfo=timezone.utc)

    step_1 = config.date_time_to_step(datetime(year=2024, month=3, day=17, hour=14, minute=1, second=7, microsecond=123000, tzinfo=timezone.utc))
    step_10 = config.date_time_to_step(datetime(year=2024, month=3, day=17, hour=14, minute=10, second=7, microsecond=123000, tzinfo=timezone.utc))
    step_777 = config.date_time_to_step(datetime(year=2024, month=3, day=18, hour=2, minute=57, second=7, microsecond=123000, tzinfo=timezone.utc))

    assert step_1 == 1
    assert step_10 == 10
    assert step_777 == 777


def test_step_size_default() -> None:
    config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_path_file("simulation.json"),
        steps=1221,
        step_size_override=None,
    )
    assert config.step_size_in_ms == 60000


def test_step_size_override() -> None:
    config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_path_file("simulation.json"),
        steps=1221,
        step_size_override=833,
    )
    assert config.step_size_in_ms == 833


def test_pace_default() -> None:
    config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_path_file("simulation.json"),
        steps=1221,
    )
    assert config.pace == 1.0


def test_pace_override() -> None:
    config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_path_file("simulation.json"),
        steps=1221,
        pace=0.3,
    )
    assert config.pace == 0.3
