import shutil
from enum import Enum
from pathlib import Path
from typing import Iterable

from ecosim_client_matlab.matlab_config import MatlabConfig
from ecosim_common.config.client_id import ClientID
from ecosim_test_common.resources.resource_utils import fmu2_fmc_path, fmu2_model_path, fmu3_fmc_path, fmu3_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu

from integration_tests.test_data.write_ini import Sections, write_client_ini, write_fmc


class ClientKind(Enum):
    FMU2 = "fmu2"
    FMU3 = "fmu3"
    PYRO5 = "pyro5"
    MATLAB = "matlab"


def _fmu_module(directory: Path, client_type: str, fmu_file: Path, fmc_file: Path) -> None:
    shutil.copy(fmu_file, directory)
    shutil.copy(fmc_file, directory)
    write_client_ini(directory, client_type, directory.name, fmc_file.name, {"fmu": {"fmu_file": f"[{fmu_file.name}]"}})


def _script_module(directory: Path, client_type: str, scripts: Iterable[str], extra_sections: Sections) -> None:
    for script in scripts:
        (directory / script).write_text("")
    write_client_ini(directory, client_type, directory.name, write_fmc(directory, inputs=["u"], outputs=["y"]), extra_sections)


def write_client_module(simulator_dir: Path, kind: ClientKind) -> ClientID:
    directory = simulator_dir / f"{kind.value}_model"
    directory.mkdir()
    match kind:
        case ClientKind.FMU2:
            _fmu_module(directory, "fmu2", fmu2_model_path(), fmu2_fmc_path())
        case ClientKind.FMU3:
            _fmu_module(directory, "fmu3", fmu3_model_path(), fmu3_fmc_path())
        case ClientKind.PYRO5:
            # the Pyro5 proxy connects lazily, starting the client needs no running Pyro5 daemon
            _script_module(
                directory=directory,
                client_type="pyro5",
                scripts=["model.py"],
                extra_sections={"pyro": {"pyro_host": "localhost", "pyro_port": "9091", "pyro_object_name": "model"}},
            )
        case ClientKind.MATLAB:
            # the Matlab engine starts with the simulation, starting the client needs no Matlab installation
            _script_module(
                directory=directory,
                client_type="matlab",
                scripts=MatlabConfig.SCRIPT_NAMES,
                extra_sections={"matlab": {"scriptfolder": str(directory)}},
            )
    # 'write_client_ini' names the simulator after its client type, which is the kind's value
    return ClientID(model_name=directory.name, simulator_name=kind.value)


def write_fmu2_module_that_names_a_missing_fmu(simulator_dir: Path) -> ClientID:
    directory = simulator_dir / "missing_fmu2_model"
    directory.mkdir()
    # the FMU in the folder gives the client type, the missing one in the ini stops the client on its worker
    shutil.copy(fmu2_model_path(), directory)
    shutil.copy(fmu2_fmc_path(), directory)
    write_client_ini(
        directory=directory,
        client_type="fmu2",
        model_name=directory.name,
        fmc_file=fmu2_fmc_path().name,
        extra_sections={"fmu": {"fmu_file": "[missing.fmu]"}},
    )
    return ClientID(model_name=directory.name, simulator_name=ClientKind.FMU2.value)


def write_broken_fmu2_module(simulator_dir: Path) -> ClientID:
    directory = simulator_dir / "broken_fmu2_model"
    directory.mkdir()
    broken_fmu_file = generate_broken_fmu(fmu_file=fmu2_model_path(), directory=simulator_dir)
    _fmu_module(directory=directory, client_type="fmu2", fmu_file=broken_fmu_file, fmc_file=fmu2_fmc_path())
    return ClientID(model_name=directory.name, simulator_name=ClientKind.FMU2.value)
