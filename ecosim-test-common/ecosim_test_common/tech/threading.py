import threading
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def exceptions_raised_in_threads() -> Iterator[list[BaseException | None]]:
    raised: list[BaseException | None] = []
    previous_hook = threading.excepthook
    threading.excepthook = lambda args: raised.append(args.exc_value)
    try:
        yield raised
    finally:
        threading.excepthook = previous_hook
