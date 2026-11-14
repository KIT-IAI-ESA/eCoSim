"""Imports a Python model as its client does at its start. The check runs it in a process of its own."""

import sys
from pathlib import Path

from ecosim_client_python.model_import import import_model_factory
from ecosim_client_python.python_config import PythonConfig
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.one_line_errors import one_line_message


def main(ini_file: Path) -> int:
    try:
        import_model_factory(config=PythonConfig.of(config_parser=ConfigParser(ini_file)))
    except Exception as error:
        # the last line, after anything the module printed
        print(one_line_message(error=error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(ini_file=Path(sys.argv[1])))
