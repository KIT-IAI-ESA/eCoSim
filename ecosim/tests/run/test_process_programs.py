import sys
from pathlib import Path

import pytest
from ecosim.run.process_programs import client_program
from ecosim_common.client.config.client_type import ClientType


@pytest.mark.parametrize(
    "client_type, package",
    [(ClientType.FMU_2, "ecosim_client_fmu_v2"), (ClientType.FMU_3, "ecosim_client_fmu_v3"), (ClientType.Python, "ecosim_client_python")],
)
def test_a_client_of_this_environment_starts_with_its_python(client_type: ClientType, package: str) -> None:
    assert client_program(client_type=client_type, simulator_directory_path=Path("Modules/house")) == [sys.executable, "-m", f"{package}.main"]


def test_a_client_that_is_not_installed_says_how_to_install_it(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as error:
        # neither this environment nor the empty search path has the MATLAB client
        client_program(client_type=ClientType.Matlab, simulator_directory_path=Path("Modules/controller"), search_path=str(tmp_path))

    assert str(error.value).startswith("Modules/controller is a MATLAB model, but ecosim-client-matlab is not installed. Install the MATLAB client")
