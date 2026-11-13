from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import Pyro5.api
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig

from integration_tests.test_data.test_client_data import TestClientData
from integration_tests.test_data.write_ini import write_client_ini, write_fmc


@Pyro5.api.expose
class Pyro5CountingModel:
    """Counts its steps, so the stored values show that every step reached the Pyro object."""

    OUTPUT = "y"
    OBJECT_NAME = "counting_model"

    def __init__(self) -> None:
        self.steps = 0

    def initialize(self) -> dict[str, float]:
        return {Pyro5CountingModel.OUTPUT: 0.0}

    def do_step(self, inputs: dict[str, float]) -> dict[str, float]:
        self.steps += 1
        return {Pyro5CountingModel.OUTPUT: float(self.steps)}

    def clear(self) -> None:
        pass


@dataclass(frozen=True)
class Pyro5TestModule:
    path: Path
    client_id: ClientID
    simulation_config: SimulationConfig
    client_data: TestClientData
    steps: int = 5

    @staticmethod
    def generate_pyro5_module(simulator_dir: Path, pyro_port: int, pyro_host: str = "localhost") -> Pyro5TestModule:
        client_data = TestClientData.with_output(simulator_name="pyro5", model_name="pyro5_model", output_name=Pyro5CountingModel.OUTPUT)
        directory = simulator_dir / client_data.model_name
        directory.mkdir()
        (directory / "model.py").touch()
        pyro_section = {"pyro_host": pyro_host, "pyro_port": str(pyro_port), "pyro_object_name": Pyro5CountingModel.OBJECT_NAME}
        write_client_ini(
            directory,
            "pyro5",
            client_data.model_name,
            write_fmc(directory, inputs=[], outputs=[Pyro5CountingModel.OUTPUT]),
            {"pyro": pyro_section},
        )
        steps: int = 5
        return Pyro5TestModule(
            path=simulator_dir,
            client_id=client_data.to_client_simulator_config().client_id,
            client_data=client_data,
            simulation_config=Pyro5TestModule._simulation_config_of(client_data, steps),
            steps=steps,
        )

    @staticmethod
    def _simulation_config_of(
        client_data: TestClientData,
        steps: int,
    ) -> SimulationConfig:
        return SimulationConfig(
            clients=[client_data.to_client_simulator_config()],
            start_date=datetime(2025, 1, 1),
            logical_delays=[],
            pace=1.0,
            steps=steps,
            step_size_in_ms=1_000,
            restore=False,
        )
