from __future__ import annotations

import os
import re
import socket
from typing import List, Sequence

from server_client.performance.tooling.time_statistic import TimeStatistic

GITHUB_CI_MACHINE = "github_ci_default"
DEFAULT_MACHINE_NAME_FOR_FALLBACK_LOCAL_REPOSITORY = "local_tuxedo_infinity_book_pro_15_gen9_amd"
CI_TOLERANCE = 0.15
LOCAL_TOLERANCE = 0.10


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


def tolerance_for(machine_name: str) -> float:
    return CI_TOLERANCE if machine_name == GITHUB_CI_MACHINE else LOCAL_TOLERANCE


def filter_slower_then_expected_times(statistics: Sequence[TimeStatistic], tolerance: float) -> List[TimeStatistic]:
    """The times that are slower than expected by more than `tolerance`; being faster is fine."""
    return [statistic for statistic in statistics if statistic.is_slower_than(tolerance)]
