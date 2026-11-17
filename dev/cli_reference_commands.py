"""The commands of the command-line reference and their parsers."""

import argparse
import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Command:
    title: str
    # modules with a CONSOLE_SCRIPT, one for each command of the section
    console_script_modules: list[str]
    # "package.module.Class" of the AppConfig with the options
    arguments: str
    note: str = ""


COMMANDS = [
    Command(
        title="Server",
        console_script_modules=["ecosim_server.config.cli_arguments"],
        arguments="ecosim_server.config.cli_arguments.CLIArguments",
    ),
    Command(
        title="FMU clients",
        console_script_modules=["ecosim_client_fmu_v2.main", "ecosim_client_fmu_v3.main"],
        arguments="ecosim_common_fmpy.config.fmpy_cli_arguments.FMPyCliArguments",
    ),
    Command(
        title="MATLAB and Pyro5 clients",
        console_script_modules=["ecosim_client_matlab.main", "ecosim_client_pyro5.main"],
        arguments="ecosim_common.client.config.cli_arguments.CLIArguments",
        note="See the [MATLAB client](../guides/matlab-client.md) and the [Pyro5 client](../guides/pyro5-client.md) guides.",
    ),
    Command(
        title="HPC",
        console_script_modules=["ecosim_hpc.config.cli_arguments"],
        arguments="ecosim_hpc.config.cli_arguments.HPCServerCliArguments",
        note="See the [HPC cluster](../guides/hpc-cluster.md) guide.",
    ),
]


def load(target: str) -> Any:
    """Import "package.module.Name"."""
    module, name = target.rsplit(".", 1)
    return getattr(importlib.import_module(module), name)


def parsers_of(command: Command) -> list[argparse.ArgumentParser]:
    create_parser = load("ecosim_common.config.app_config.create_parser")
    parameters = load(command.arguments).parameters()
    return [
        create_parser(console_script=load(f"{module}.CONSOLE_SCRIPT"), parameters=parameters, environment_variables={})
        for module in command.console_script_modules
    ]
