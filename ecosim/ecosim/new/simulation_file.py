from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ecosim_common.config.interface_type import InterfaceType
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface

from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel
from ecosim.new.wiring import Connection, Wiring


@dataclass(frozen=True)
class SimulationFile:
    """The simulation.json of the new simulation: every model with its connected inputs and all its outputs."""

    models: list[SimulationModel]
    wiring: Wiring
    length: SimulationLength

    def as_json(self) -> str:
        content = {
            "simulators": [self._simulator(model=model) for model in self.models],
            "logical_delays": [],
            "setup": {
                "delta_t": self.length.step_size_in_milliseconds,
                "steps": self.length.steps,
                "start_date": self.length.start_date.isoformat(),
            },
        }
        return json.dumps(content, indent=2) + "\n"

    def _simulator(self, model: SimulationModel) -> dict[str, Any]:
        # an input without a connection fails the connection check of the server, so the open ones are only in the .fmc file
        inputs = [
            {**_interface(interface=interface, interface_type=InterfaceType.INPUT), "connected_to": [self._target_of(connection=connection)]}
            for interface, address in zip(model.interfaces.inputs, model.input_addresses(), strict=True)
            if (connection := self.wiring.connection_of(address=address)) is not None
        ]
        outputs = [_interface(interface=interface, interface_type=InterfaceType.OUTPUT) for interface in model.interfaces.outputs]
        return {"name": model.name, "model": model.name, "interfaces": [*inputs, *outputs]}

    def _target_of(self, connection: Connection) -> dict[str, Any]:
        # the server finds the simulator of an output by its position in simulators
        position = next(position for position, model in enumerate(self.models) if model.name == connection.output.model)
        return {"simulator": position, "interface": connection.output.name}


def _interface(interface: FMUInterface, interface_type: InterfaceType) -> dict[str, Any]:
    return {"name": interface.name, "type": interface_type.value.capitalize(), "unit": interface.unit, "description": interface.description}
