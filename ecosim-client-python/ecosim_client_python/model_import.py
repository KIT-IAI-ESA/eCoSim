import importlib
import importlib.machinery
import pkgutil
import sys
from types import ModuleType
from typing import Any, Callable

from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.one_line_errors import one_line_message

from ecosim_client_python.python_config import PythonConfig


def import_model_factory(config: PythonConfig) -> Callable[[], Any]:
    module = _import_model_module(config=config)
    model_factory = getattr(module, config.class_name, None)
    if model_factory is None:
        module_location = getattr(module, "__file__", None) or module.__name__
        public_names = [name for name in dir(module) if not name.startswith("_")]
        raise AttributeError(f"{module_location} has no {config.class_name}.{did_you_mean(name=config.class_name, known_names=public_names)}")
    if not callable(model_factory):
        raise TypeError(f"{config.model_reference} is not a class. Its type is {type(model_factory).__name__}")
    return model_factory


def _import_model_module(config: PythonConfig) -> ModuleType:
    _ensure_not_loaded_from_another_directory(config=config)
    if str(config.directory) not in sys.path:
        sys.path.insert(0, str(config.directory))
    # finds a module file written after the last import
    importlib.invalidate_caches()
    try:
        return importlib.import_module(config.module_name)
    except ModuleNotFoundError as error:
        raise _module_not_found_error(config=config, missing_module=error.name) from error
    except Exception as error:
        raise ImportError(f"The model {config.model_reference} failed while its module was imported: {one_line_message(error=error)}") from error


def _module_not_found_error(config: PythonConfig, missing_module: str | None) -> ModuleNotFoundError:
    if missing_module is None or f"{config.module_name}.".startswith(f"{missing_module}."):
        return ModuleNotFoundError(_why_the_module_is_missing(config=config), name=missing_module)
    return ModuleNotFoundError(
        f"{missing_module} is not installed in the Python environment of this client. The model {config.model_reference} imports it",
        name=missing_module,
    )


def _why_the_module_is_missing(config: PythonConfig) -> str:
    if config.module_name.endswith(".py"):
        return (
            f"model in [python] needs the module without .py. Use model = {config.module_name.removesuffix('.py')}:{config.class_name}, "
            + f"not '{config.model_reference}'"
        )
    message = f"No module {config.module_name} in {config.directory}, and none is installed"
    modules_in_directory = [module.name for module in pkgutil.iter_modules(path=[str(config.directory)])]
    hint = did_you_mean(name=config.module_name, known_names=modules_in_directory)
    return f"{message}.{hint}" if hint else message


def _ensure_not_loaded_from_another_directory(config: PythonConfig) -> None:
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
