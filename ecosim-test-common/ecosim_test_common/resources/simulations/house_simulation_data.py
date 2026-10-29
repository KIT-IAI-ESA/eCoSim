import csv
from pathlib import Path
from typing import ClassVar

from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType

from ecosim_test_common.resources.resource_utils import resource_path_file

ExpectedResultEntry = dict[str, InterfaceValueType]


class HouseSimulationData:
    """
    The houses scenario: a weather model drives a house, whose room temperature is fed back - delayed by one step -
    into a heating and a ventilation controller. All four are FMI 2.0 FMUs (linux64 binaries only).
    """

    RESOURCES: ClassVar[Path] = resource_path_file("integration/models/houses")
    SIMULATION_CONFIG_FILE: ClassVar[Path] = RESOURCES / "simulation.json"
    # the module names are used as keys and for building paths -> do not change them
    MODULES: ClassVar[tuple[str, ...]] = ("weather", "house", "heating", "ventilation")
    # the expected results were recorded with 200 steps of 60s step size
    STEPS: ClassVar[int] = 200

    @staticmethod
    def client_config_file(module: str) -> Path:
        return HouseSimulationData.RESOURCES / f"{module}_preferences_linux.ini"

    @staticmethod
    def expected_rows(module: str) -> list[ExpectedResultEntry]:
        with open(HouseSimulationData.RESOURCES / "expected" / f"{module}.csv", newline="") as file:
            return [{column[2:]: float(value) for column, value in row.items() if not column.endswith("_json")} for row in csv.DictReader(file)]
