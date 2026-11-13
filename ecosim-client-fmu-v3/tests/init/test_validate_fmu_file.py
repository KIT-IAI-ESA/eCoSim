import subprocess
import sys

from ecosim_test_common.resources.resource_utils import fmu3_model_path


def test_the_client_validates_its_own_fmu() -> None:
    config_file = fmu3_model_path().parent / "configs" / "state_space.ini"

    result = subprocess.run(
        [sys.executable, "-m", "ecosim_client_fmu_v3.main", "--validate-fmu-file-only", "--config-file", str(config_file)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
