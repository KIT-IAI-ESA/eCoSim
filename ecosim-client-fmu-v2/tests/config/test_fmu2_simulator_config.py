from pathlib import Path

import pytest
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu2_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu


def test_retry_reads_a_model_description_that_fails_the_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # the retry extracts the FMU into ./failed_fmus
    monkeypatch.chdir(tmp_path)
    # fmpy finds ./modelDescription.xml only in the extracted FMU
    fmu_file = generate_broken_fmu(fmu_file=fmu2_model_path(), directory=tmp_path, model_description_entry="./modelDescription.xml")

    model_description = FMU2SimulatorConfig.read_model_description(fmu_config=FMUBaseConfig(fmu_file=fmu_file))

    assert model_description.modelName == "Feedthrough"
