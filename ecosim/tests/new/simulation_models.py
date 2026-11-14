from pathlib import Path
from typing import Sequence

from ecosim.check.findings import Findings
from ecosim.check.simulation_check import SimulationCheck
from ecosim.new.simulation_model import SimulationModel
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface, FMUInterfaces


def create_interface(name: str, unit: str = "", shape: tuple[int, ...] = ()) -> FMUInterface:
    return FMUInterface(name=name, unit=unit, description="", start="0", shape=shape)


def create_model(name: str, inputs: Sequence[str | FMUInterface] = (), outputs: Sequence[str | FMUInterface] = ()) -> SimulationModel:
    """A model of an FMI 2.0 FMU that is never read. A name stands for an interface without a unit."""
    interfaces = FMUInterfaces(
        fmu_file=Path(f"{name}.fmu"),
        fmi_version="2.0",
        inputs=tuple(create_interface(name=interface) if isinstance(interface, str) else interface for interface in inputs),
        outputs=tuple(create_interface(name=interface) if isinstance(interface, str) else interface for interface in outputs),
        skipped=(),
    )
    return SimulationModel(name=name, interfaces=interfaces)


def create_check_without_findings() -> SimulationCheck:
    return create_check_with_problems(problems=[])


def create_check_with_problems(problems: list[str]) -> SimulationCheck:
    findings = Findings(problems=problems)
    return SimulationCheck(findings=findings, simulators=[], simulator_count=None, simulation_config=None, server_config=None, length_is_known=False)
