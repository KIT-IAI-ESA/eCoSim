import sys
from functools import wraps
from typing import Callable, Protocol, Sequence

from ecosim_common.tech.shutdown_manager import ShutdownManager

DEBUG_HINT = "(run with --debug for the full traceback)"


class Main[Result](Protocol):
    def __call__(self, passed_arguments: Sequence[str] | None = None) -> Result: ...


def exits_with_one_line_errors[Result](program_name: str) -> Callable[[Callable[[Sequence[str]], Result]], Main[Result]]:
    def decorate(main: Callable[[Sequence[str]], Result]) -> Main[Result]:
        @wraps(main)
        def main_with_one_line_errors(passed_arguments: Sequence[str] | None = None) -> Result:
            arguments = sys.argv[1:] if passed_arguments is None else passed_arguments
            try:
                return main(arguments)
            except Exception as error:
                if "--debug" in arguments:
                    raise
                sys.stdout.flush()
                print(_error_line(program_name=program_name, error=error), file=sys.stderr, flush=True)
                sys.exit(ShutdownManager.FAILED_RUN_EXIT_CODE)

        return main_with_one_line_errors

    return decorate


def one_line_message(error: Exception) -> str:
    if isinstance(error, OSError) and error.strerror:
        # str() of an OSError adds "[Errno 2]" and quotes
        return f"{error.strerror}: {error.filename}" if error.filename else error.strerror
    message = str(error)
    if not message:
        return type(error).__name__
    # str() of a KeyError is only the key
    return f"{type(error).__name__}: {message}" if isinstance(error, KeyError) else message


def _error_line(program_name: str, error: Exception) -> str:
    message = one_line_message(error=error)
    separator = "\n" if "\n" in message else " "
    return f"{program_name}: error: {message}{separator}{DEBUG_HINT}"
