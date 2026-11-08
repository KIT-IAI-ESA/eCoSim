from pathlib import Path

from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu3_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu


def test_reads_a_model_description_that_fails_the_schema(tmp_path: Path) -> None:
    fmu_config = FMUBaseConfig(fmu_file=generate_broken_fmu(fmu_file=fmu3_model_path(), directory=tmp_path))

    simulator_config = FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config)

    assert simulator_config.model_name() == "StateSpace"
