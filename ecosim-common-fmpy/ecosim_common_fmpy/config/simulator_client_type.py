from pathlib import Path

from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory

from ecosim_common_fmpy.tech.read_model_description import read_model_description


def client_type_of(simulator_directory: SimulatorDirectory) -> ClientType:
    """The one client that runs the model of a simulator directory."""
    # a Python model can sit next to other files, a .py helper or an FMU it loads itself
    if simulator_directory.names_a_python_model():
        return ClientType.Python
    model_files = _model_files_of_one_model(simulator_directory=simulator_directory)
    match model_files[0].suffix:
        case ".fmu":
            return client_type_of_fmi_version(fmi_version=read_model_description(file=model_files[0]).fmiVersion, fmu_file=model_files[0])
        case ".m":
            return ClientType.Matlab
        case _:
            return ClientType.Pyro5


def client_type_of_fmi_version(fmi_version: str, fmu_file: Path) -> ClientType:
    match fmi_version.split(".")[0]:
        case "2":
            return ClientType.FMU_2
        case "3":
            return ClientType.FMU_3
    raise ValueError(f"{fmu_file} is FMI {fmi_version}, but eCoSim runs FMI 2.0 and FMI 3.0 FMUs only.")


def _model_files_of_one_model(simulator_directory: SimulatorDirectory) -> list[Path]:
    model_files = simulator_directory.model_files()
    names = ", ".join(model_file.name for model_file in model_files)
    if not model_files:
        raise ValueError(
            f"{simulator_directory.path} has no model. Put an .fmu, .m or .py file in it, "
            + "or write model = <module>:<class> in the [python] section of its ini file.",
        )
    if len({model_file.suffix for model_file in model_files}) > 1:
        raise ValueError(f"{simulator_directory.path} holds model files of different kinds: {names}. A simulator folder holds one model.")
    if model_files[0].suffix == ".fmu" and len(model_files) > 1:
        raise ValueError(f"{simulator_directory.path} holds several FMUs: {names}. A simulator folder holds one model.")
    return model_files
