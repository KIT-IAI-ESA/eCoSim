from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.close_name import did_you_mean

# interface names share long prefixes like weatherBus_, so only a near match is a likely typo
INTERFACE_NAME_CUTOFF = 0.9


@dataclass(frozen=True)
class InterfaceMismatch:
    """The interfaces that the simulation config and the .fmc file of one client name differently."""

    inputs_not_in_fmc: List[InterfaceId]
    outputs_not_in_fmc: List[InterfaceId]
    required_inputs_not_connected: List[InterfaceId]
    fmc_inputs: List[InterfaceId]
    fmc_outputs: List[InterfaceId]

    def lines(self, fmc_file: str) -> List[str]:
        return [
            *(self._input_line(name=name, fmc_file=fmc_file) for name in self.inputs_not_in_fmc),
            *(self._output_line(name=name, fmc_file=fmc_file) for name in self.outputs_not_in_fmc),
            *(self._required_line(name=name, fmc_file=fmc_file) for name in self.required_inputs_not_connected),
        ]

    def _input_line(self, name: InterfaceId, fmc_file: str) -> str:
        hint = did_you_mean(name=name, known_names=self.fmc_inputs, cutoff=INTERFACE_NAME_CUTOFF)
        return f"The simulation config connects input {name}, but {fmc_file} has no input of that name.{hint}"

    def _output_line(self, name: InterfaceId, fmc_file: str) -> str:
        hint = did_you_mean(name=name, known_names=self.fmc_outputs, cutoff=INTERFACE_NAME_CUTOFF)
        return f"The simulation config reads output {name}, but {fmc_file} has no output of that name.{hint}"

    @staticmethod
    def _required_line(name: InterfaceId, fmc_file: str) -> str:
        return f"{fmc_file} marks input {name} as required, but the simulation config does not connect it."
