from __future__ import annotations

import importlib
import importlib.util
import socket
import subprocess
import sys
from pathlib import Path
from typing import assert_never

from ecosim_client_python.python_config import PythonConfig
from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings

from ecosim.check.findings import Findings, problem_of_ini_file, with_the_file
from ecosim.check.fmu_check import ModelCheck, fmu_check

IMPORT_TIMEOUT_IN_SECONDS = 60


def model_check(
    directory: SimulatorDirectory,
    client_type: ClientType,
    client_config: ClientConfig,
    server_interface_settings: ServerInterfaceSettings,
    before_a_run: bool,
) -> ModelCheck:
    match client_type:
        case ClientType.FMU_2 | ClientType.FMU_3:
            return fmu_check(directory=directory, client_config=client_config, server_interface_settings=server_interface_settings)
        case ClientType.Matlab:
            return ModelCheck(findings=_matlab_findings(directory=directory))
        case ClientType.Pyro5:
            return ModelCheck(findings=_pyro_findings(directory=directory, before_a_run=before_a_run))
        case ClientType.Python:
            return ModelCheck(findings=_python_findings(directory=directory))
        case _:
            assert_never(client_type)


def _matlab_findings(directory: SimulatorDirectory) -> Findings:
    # the MATLAB client needs Python 3.12 and often has its own environment
    if importlib.util.find_spec("ecosim_client_matlab") is None:
        return Findings(warnings=[f"{directory.path}: [matlab] was not checked. ecosim-client-matlab is not installed."])
    try:
        importlib.import_module("ecosim_client_matlab.matlab_config").MatlabConfig(directory.config_parser)
    except Exception as error:
        return Findings(problems=[problem_of_ini_file(error=error, ini_file=directory.config_parser.config_file)])
    return Findings()


def _pyro_findings(directory: SimulatorDirectory, before_a_run: bool) -> Findings:
    config_parser = directory.config_parser
    try:
        installed = importlib.util.find_spec("ecosim_client_pyro5") is not None
        if installed:
            importlib.import_module("ecosim_client_pyro5.pyro_config").PyroConfig.of(config_parser)
        host, port = config_parser.get_string("pyro", "pyro_host"), config_parser.get_int("pyro", "pyro_port")
    except Exception as error:
        return Findings(problems=[problem_of_ini_file(error=error, ini_file=config_parser.config_file)])
    not_installed = f"{directory.path}: only pyro_host and pyro_port of [pyro] were checked. ecosim-client-pyro5 is not installed."
    findings = Findings(warnings=[] if installed else [not_installed])
    try:
        # the Pyro5 object is started separately
        socket.create_connection(address=(host, port), timeout=1).close()
    except OSError:
        nothing_listens = (
            f"{config_parser.config_file}: nothing listens on pyro_host {host} and pyro_port {port}. Start the Pyro5 object before the run. "
            + "If it runs already, set pyro_host and pyro_port to the address it listens on."
        )
        (findings.problems if before_a_run else findings.warnings).append(nothing_listens)
    return findings


def _python_findings(directory: SimulatorDirectory) -> Findings:
    ini_file = directory.config_parser.config_file
    try:
        PythonConfig.of(config_parser=directory.config_parser)
    except Exception as error:
        return Findings(problems=[problem_of_ini_file(error=error, ini_file=ini_file)])
    try:
        problem = _python_model_import_problem(ini_file=ini_file)
    except subprocess.TimeoutExpired:
        return Findings(warnings=[f"{ini_file}: the import of the model took more than {IMPORT_TIMEOUT_IN_SECONDS} s. It was not checked."])
    return Findings(problems=[] if problem is None else [with_the_file(message=problem, file=ini_file)])


def _python_model_import_problem(ini_file: Path) -> str | None:
    # in a subprocess, two simulators can have modules with the same name
    imported = subprocess.run(
        [sys.executable, "-P", "-m", "ecosim.check.python_model_import", str(ini_file.absolute())],
        capture_output=True,
        text=True,
        check=False,
        timeout=IMPORT_TIMEOUT_IN_SECONDS,
    )
    if imported.returncode == 0:
        return None
    lines = imported.stdout.splitlines()
    return lines[-1] if imported.returncode == 1 and lines else f"the import of the model ended with exit code {imported.returncode}."
