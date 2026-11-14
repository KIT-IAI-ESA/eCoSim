from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

import pytest
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.postgres_name_check import check_names_fit_postgres_storage

START_DATE = datetime(year=2024, month=1, day=1, tzinfo=timezone.utc)


def generate_model_interface_server(simulator_name: str, model_name: str, interface_name: str, interface_type: InterfaceType) -> ModelInterfaceServer:
    model_interface_id = ModelInterfaceId(model_name=model_name, interface=interface_name)
    return ModelInterfaceServer(
        simulator_interface_id=SimulatorInterfaceId(simulator_name=simulator_name, model_interface_id=model_interface_id),
        name=interface_name,
        unit="",
        description="",
        interface_type=interface_type,
        required=False,
        connected_to=[],
    )


def generate_client_simulator_config(
    simulator_name: str,
    interfaces: Sequence[tuple[str, InterfaceType]] = (),
    model_name: str | None = None,
) -> ClientSimulatorConfig:
    model_name = model_name or simulator_name
    return ClientSimulatorConfig(
        simulator_name=simulator_name,
        model_name=model_name,
        client_id=ClientID(model_name=model_name, simulator_name=simulator_name),
        interfaces=[
            generate_model_interface_server(
                simulator_name=simulator_name,
                model_name=model_name,
                interface_name=interface_name,
                interface_type=interface_type,
            )
            for interface_name, interface_type in interfaces
        ],
    )


def generate_simulation_config(
    clients: Sequence[ClientSimulatorConfig],
    restore: bool = False,
    steps: int = 1,
    step_size_in_ms: int = 1000,
) -> SimulationConfig:
    return SimulationConfig(
        clients=list(clients),
        steps=steps,
        step_size_in_ms=step_size_in_ms,
        start_date=START_DATE,
        logical_delays=[],
        restore=restore,
    )


def error_of(*clients: ClientSimulatorConfig) -> str:
    with pytest.raises(RuntimeError) as error:
        check_names_fit_postgres_storage(generate_simulation_config(clients=clients))
    return str(error.value)
