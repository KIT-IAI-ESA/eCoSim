import importlib.machinery
import pkgutil
import sys
from typing import Any, Callable

from ecosim_common.tech.one_line_errors import one_line_message

from ecosim_client_python.python_config import PythonConfig
from ecosim_client_python.python_model import PythonModel


def import_model_factory(config: PythonConfig) -> Callable[[], Any]:
    _ensure_not_loaded_from_another_directory(config=config)
    if str(config.directory) not in sys.path:
        sys.path.insert(0, str(config.directory))
    model_factory: Callable[[], Any] = pkgutil.resolve_name(config.model_reference)
    return model_factory


def create_model(config: PythonConfig) -> PythonModel:
    try:
        model = import_model_factory(config=config)()
    except Exception as error:
        raise RuntimeError(f"The model {config.model_reference} could not be loaded: {one_line_message(error=error)}") from error
    if not isinstance(model, PythonModel):
        raise TypeError(f"{config.model_reference} needs initialize(), do_step(inputs, current_simulation_time, step_size_in_seconds) and clear()")
    return model


def _ensure_not_loaded_from_another_directory(config: PythonConfig) -> None:
    # several clients of an HPC run share a process
    top_level_name = config.module_name.partition(".")[0]
    loaded_module = sys.modules.get(top_level_name)
    module_in_directory = importlib.machinery.PathFinder.find_spec(fullname=top_level_name, path=[str(config.directory)])
    loaded_file = getattr(loaded_module, "__file__", None)
    if loaded_module is None or module_in_directory is None or loaded_file == module_in_directory.origin:
        return
    raise ImportError(
        f"A module {top_level_name} is already loaded from {loaded_file or 'Python itself'}. "
        + f"Rename {module_in_directory.origin} and change model in the ini file",
    )
