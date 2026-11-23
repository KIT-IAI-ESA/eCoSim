from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface, FMUInterfaces

from ecosim.new.simulation_model_interface_id import SimulationModelInterfaceId

# a model name is also a folder name and a part of a PostgreSQL table name
NOT_IN_A_MODEL_NAME = re.compile(r"[^A-Za-z0-9_-]")


@dataclass(frozen=True)
class SimulationModel:
    # the name of the simulator and of the model
    name: str
    interfaces: FMUInterfaces

    @staticmethod
    def of_arguments(arguments: list[str]) -> list[SimulationModel]:
        named_files = [named_file for argument in arguments for named_file in _named_fmu_files(argument=argument)]
        for name, fmu_file in named_files:
            _ensure_it_can_be_a_model_name(name=name, fmu_file=fmu_file)
        _ensure_unique_names(named_files=named_files)
        return [SimulationModel(name=name, interfaces=_interfaces_of(fmu_file=fmu_file)) for name, fmu_file in named_files]

    def input_ids(self) -> list[SimulationModelInterfaceId]:
        return [SimulationModelInterfaceId(model=self.name, name=interface.name) for interface in self.interfaces.inputs]

    def output_ids(self) -> list[SimulationModelInterfaceId]:
        return [SimulationModelInterfaceId(model=self.name, name=interface.name) for interface in self.interfaces.outputs]


def input_at(models: list[SimulationModel], interface_id: SimulationModelInterfaceId) -> FMUInterface:
    interface = model_named(models=models, name=interface_id.model).interfaces.input_named(name=interface_id.name)
    if interface is None:
        raise KeyError(f"{interface_id} is not an input")
    return interface


def output_at(models: list[SimulationModel], interface_id: SimulationModelInterfaceId) -> FMUInterface:
    interface = model_named(models=models, name=interface_id.model).interfaces.output_named(name=interface_id.name)
    if interface is None:
        raise KeyError(f"{interface_id} is not an output")
    return interface


def model_named(models: list[SimulationModel], name: str) -> SimulationModel:
    return next(model for model in models if model.name == name)


def _named_fmu_files(argument: str) -> list[tuple[str, Path]]:
    name, separator, file = argument.partition("=")
    # a file name can have an equals sign too
    if separator and not Path(argument).exists():
        return [(name, _fmu_file(path=Path(file)))]
    path = Path(argument)
    if path.is_dir():
        return [(_name_of(fmu_file=fmu_file), fmu_file) for fmu_file in _fmu_files_in(directory=path)]
    fmu_file = _fmu_file(path=path)
    return [(_name_of(fmu_file=fmu_file), fmu_file)]


def _fmu_file(path: Path) -> Path:
    if path.is_dir():
        raise ValueError(f"{path} is a folder, but NAME=FILE takes one .fmu file.")
    if not path.is_file():
        fmu_files_next_to_it = [fmu_file.name for fmu_file in _fmu_files_of(directory=path.parent)]
        raise ValueError(f"There is no file {path}.{did_you_mean(name=path.name, known_names=fmu_files_next_to_it)}")
    if path.suffix.lower() != ".fmu":
        raise ValueError(f"{path} is not an .fmu file.")
    return path


def _fmu_files_in(directory: Path) -> list[Path]:
    fmu_files = _fmu_files_of(directory=directory)
    if not fmu_files:
        raise ValueError(f"The folder {directory} has no .fmu files. The folders in it are not searched.")
    return fmu_files


def _fmu_files_of(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".fmu")


def _name_of(fmu_file: Path) -> str:
    return NOT_IN_A_MODEL_NAME.sub(repl="_", string=fmu_file.stem)


def _ensure_it_can_be_a_model_name(name: str, fmu_file: Path) -> None:
    if not name or NOT_IN_A_MODEL_NAME.search(name):
        example = _name_of(fmu_file=Path(name)) or _name_of(fmu_file=fmu_file)
        raise ValueError(f"'{name}' cannot be a model name. Use letters, digits, '_' and '-', like {example}={fmu_file}")
    if name.lower() in {"con", "prn", "aux", "nul", *(f"{device}{number}" for device in ("com", "lpt") for number in range(10))}:
        raise ValueError(f"'{name}' cannot be a model name. Windows reserves it for a device. Use another name, like {name}_model={fmu_file}")


def _ensure_unique_names(named_files: list[tuple[str, Path]]) -> None:
    # Windows, macOS and PostgreSQL ignore the case of a name
    files_of_name: dict[str, list[tuple[str, Path]]] = {}
    for name, fmu_file in named_files:
        files_of_name.setdefault(name.lower(), []).append((name, fmu_file))
    for same_named in files_of_name.values():
        if len(same_named) > 1:
            name, second_file = same_named[0][0], same_named[1][1]
            files = ", ".join(str(fmu_file) for _, fmu_file in same_named)
            raise ValueError(f"{len(same_named)} models get the name {name}: {files}. Rename one of them, like {name}_2={second_file}")


def _interfaces_of(fmu_file: Path) -> FMUInterfaces:
    try:
        return FMUInterfaces.of_fmu_file(fmu_file=fmu_file)
    except Exception as error:
        message = one_line_message(error=error)
        # the messages of fmpy do not have the file
        if str(fmu_file) in message:
            raise
        # zipfile raises a KeyError for a missing item
        reason = "it has no modelDescription.xml." if isinstance(error, KeyError) and "modelDescription.xml" in message else message
        raise ValueError(f"{fmu_file} cannot be read as an FMU: {reason}") from error
