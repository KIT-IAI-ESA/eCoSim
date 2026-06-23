import logging
from typing import Any, Generator

import dask.distributed as dd
import pytest
from _pytest.logging import _LiveLoggingStreamHandler, logging_StreamHandler
from _pytest.nodes import Item
from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager

# INIT LOGGER
init_logger(log_level=logging.DEBUG)
pytest_fixture_logger = logging.getLogger("PytestFixtures")


@pytest.fixture(scope="session", autouse=True)
def remove_pytest_live_logger() -> None:
    pytest_handlers: list[logging_StreamHandler] = []
    for i, handler in enumerate(logging.root.handlers):
        if isinstance(handler, _LiveLoggingStreamHandler):
            pytest_handlers.append(handler)
    for handler in pytest_handlers:
        logging.root.removeHandler(handler)


@pytest.fixture(scope="function", autouse=True)
def setup_shutdown_manager() -> Generator[None, Any, None]:
    pytest_fixture_logger.debug("Initializing shutdown manager")
    ShutdownManager().init()
    yield None
    ShutdownManager().set_shutdown_at_application_end()
    pytest_fixture_logger.debug("Called shutdown manager at application end")
    ShutdownManager.reset_instance()


@pytest.fixture(scope="function")
def dask_client() -> Generator[dd.Client, Any, None]:
    pytest_fixture_logger.info("Creating new distributed dask client")
    client = dd.Client(n_workers=4, threads_per_worker=4)
    client.forward_logging()
    client.register_plugin(DaskLoggingPlugin(log_level=logging.DEBUG))
    yield client


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: Item, nextitem: Item | None) -> None:
    """
    This method tries to close a dask client if it is still open. This cannot be done inside
    the 'dask_client' fixture, because the fixture will be called _before_ the auto used
    'setup_shutdown_manager' fixture. This would result in errors since during shutdown
    a lot of dask stuff is done.
    """
    try:
        client = dd.get_client()
        pytest_fixture_logger.info(f"Closing dask client: {client}")
        client.close()
        client.cluster.close()
        dd.client._global_clients.clear()
    except Exception:
        pass
