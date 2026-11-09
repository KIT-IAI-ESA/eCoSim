import csv
from pathlib import Path
from typing import ClassVar

import pytest
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.executing_platform import ExecutingPlatform

from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import resource_path_file

ExpectedResultEntry = dict[str, InterfaceValue]


class HouseSimulationData:
    """
    The houses scenario: a weather model drives a house, whose room temperature is fed back - delayed by one step -
    into a heating and a ventilation controller.
    """

    RESOURCES: ClassVar[Path] = resource_path_file("fmu_v2/models/house")
    SIMULATION_CONFIG_FILE: ClassVar[Path] = RESOURCES / "simulation.json"
    # the module names are used as keys and for building paths -> do not change them
    MODULES: ClassVar[tuple[str, ...]] = ("weather", "house", "heating", "ventilation")
    # one FMU build per platform, in a folder named after the platform; all builds yield the same expected results
    PLATFORMS: ClassVar[tuple[ExecutingPlatform, ...]] = (ExecutingPlatform.LINUX, ExecutingPlatform.WINDOWS)
    # the expected results were recorded with 200 steps of 60s step size
    STEPS: ClassVar[int] = 200

    @staticmethod
    def client_config_file(module: str, platform: ExecutingPlatform | None = None) -> Path:
        platform_name = (platform or ExecutingPlatform.current()).value
        return HouseSimulationData.RESOURCES / platform_name / f"{module}_preferences_{platform_name}.ini"

    @staticmethod
    def fmu_file(module: str) -> Path:
        return HouseSimulationData.client_config_file(module).parent / f"{module}.fmu"

    @staticmethod
    def skip_unless_fmpy_loads_the_fmus() -> pytest.MarkDecorator:
        platform = ExecutingPlatform.current()
        if platform not in HouseSimulationData.PLATFORMS:
            return pytest.mark.skip(reason=f"There is no build of the house FMUs for {platform.value}")
        return skip_unless_fmpy_loads(*[HouseSimulationData.fmu_file(module) for module in HouseSimulationData.MODULES])

    @staticmethod
    def expected_rows(module: str) -> list[ExpectedResultEntry]:
        with open(HouseSimulationData.RESOURCES / "expected" / f"{module}.csv", newline="") as file:
            return [{column[2:]: float(value) for column, value in row.items() if not column.endswith("_json")} for row in csv.DictReader(file)]
