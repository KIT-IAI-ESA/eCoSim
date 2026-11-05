from __future__ import annotations

import os
import re
import socket

GITHUB_CI_MACHINE = "github_ci_default"
DEFAULT_MACHINE_NAME_FOR_FALLBACK_LOCAL_REPOSITORY = "local_tuxedo_infinity_book_pro_15_gen9_amd"

CI_TOLERANCE_PRIMARY = 0.15
LOCAL_TOLERANCE_PRIMARY = 0.10
CI_TOLERANCE_SECONDARY = 1.50
LOCAL_TOLERANCE_SECONDARY = 1.20


def current_machine() -> str:
    machine = os.environ.get("ECOSIM_PERFORMANCE_MACHINE")
    if machine:
        return machine
    return "local_" + re.sub(r"[^a-z0-9]+", "_", socket.gethostname().lower())


def fallback_machine_name_for_local_repository() -> str:
    return os.environ.get("ECOSIM_MACHINE_NAME_FOR_FALLBACK_LOCAL_REPOSITORY", default=DEFAULT_MACHINE_NAME_FOR_FALLBACK_LOCAL_REPOSITORY)


def current_test_name() -> str | None:
    """The running pytest function, without the parametrization (`path::test_name[dask] (call)` -> `test_name`)."""
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    if current_test is None:
        return None
    return current_test.split("::")[-1].split(" ")[0].split("[")[0]


def is_local_machine(machine_name: str) -> bool:
    return machine_name != GITHUB_CI_MACHINE and machine_name.startswith("local_")


def primary_tolerance_for(machine_name: str) -> float:
    return CI_TOLERANCE_PRIMARY if machine_name == GITHUB_CI_MACHINE else LOCAL_TOLERANCE_PRIMARY


def secondary_tolerance_for(machine_name: str) -> float:
    return CI_TOLERANCE_SECONDARY if machine_name == GITHUB_CI_MACHINE else LOCAL_TOLERANCE_SECONDARY


def format_seconds(
    time: float | None,
) -> str:
    return "-" if time is None else f"{time:.3f}s"
