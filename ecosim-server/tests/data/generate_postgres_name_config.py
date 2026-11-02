from __future__ import annotations

from datetime import datetime, timezone

import pytest
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.postgres_name_check import check_names_fit_postgres_storage

START_DATE = datetime(year=2024, month=1, day=1, tzinfo=timezone.utc)


def an_interface(simulator: str, model: str, name: str, interface_type: InterfaceType) -> ModelInterfaceServer:
    model_interface_id = ModelInterfaceId(model_name=model, interface=name)
    return ModelInterfaceServer(
        simulator_interface_id=SimulatorInterfaceId(simulator_name=simulator, model_interface_id=model_interface_id),
        name=name,
        unit="",
        description="",
        interface_type=interface_type,
        required=False,
        connected_to=[],
    )


def a_simulator(name: str, *interfaces: tuple[str, InterfaceType], model: str | None = None) -> ClientSimulatorConfig:
    model_name = model or name
    return ClientSimulatorConfig(
        simulator_name=name,
        model_name=model_name,
        client_id=ClientID(model_name=model_name, simulator_name=name),
        interfaces=[an_interface(simulator=name, model=model_name, name=interface, interface_type=kind) for interface, kind in interfaces],
    )


def a_config(*clients: ClientSimulatorConfig) -> SimulationConfig:
    return SimulationConfig(clients=list(clients), steps=1, step_size_in_ms=1000, start_date=START_DATE, logical_delays=[])


def error_of(*clients: ClientSimulatorConfig) -> str:
    with pytest.raises(RuntimeError) as error:
        check_names_fit_postgres_storage(a_config(*clients))
    return str(error.value)
