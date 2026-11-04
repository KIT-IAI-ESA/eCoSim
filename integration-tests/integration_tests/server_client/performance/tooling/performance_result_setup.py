from __future__ import annotations

import os
import re
import socket


def current_machine() -> str:
    machine = os.environ.get("ECOSIM_PERFORMANCE_MACHINE")
    if machine:
        return machine
    return "local_" + re.sub(r"[^a-z0-9]+", "_", socket.gethostname().lower())


def current_test_name() -> str | None:
    """The running pytest function, without the parametrization (`path::test_name[dask] (call)` -> `test_name`)."""
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    if current_test is None:
        return None
    return current_test.split("::")[-1].split(" ")[0].split("[")[0]
