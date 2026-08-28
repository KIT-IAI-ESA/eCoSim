from __future__ import annotations

import logging
from typing import Any, Callable

from distributed import Variable
from distributed.scheduler import Scheduler

_logger = logging.getLogger(__name__)

_VARIABLE_EXTENSION_KEY = "variables"


def _scheduler_knows_variable(
    variable_name: str,
    dask_scheduler: Scheduler,
) -> bool:
    """Runs inside the scheduler process and answers whether the variable is already known."""
    extension = dask_scheduler.extensions.get(_VARIABLE_EXTENSION_KEY)
    if extension is None:
        return False
    return variable_name in extension.variables


class DaskVariableInitializer:
    """Initializes a dask ``Variable`` without ever reading its value."""

    @staticmethod
    def initialize(
        variable: Variable,
        value_supplier: Callable[[], Any],
        may_already_exist: bool,
    ) -> None:
        """Sets ``value`` unless the variable is already initialized on the scheduler."""
        if may_already_exist and DaskVariableInitializer.exists(variable):
            return
        variable.set(value_supplier())

    @staticmethod
    def exists(variable: Variable) -> bool:
        client = variable.client
        if client is None:
            return False
        try:
            return bool(client.run_on_scheduler(_scheduler_knows_variable, variable.name))
        except Exception as error:
            _logger.debug("Could not ask the scheduler for variable '%s': %s", variable.name, error)
            return False
