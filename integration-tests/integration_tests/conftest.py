import logging
from typing import Generator, Any

import pytest
from _pytest.nodes import Item

from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
import dask.distributed as dd


init_logger(log_level=logging.DEBUG)


@pytest.fixture(scope="function", autouse=True)
def setup_shutdown_manager() -> Generator[None, Any, None]:
    ShutdownManager().init()
    yield None
    ShutdownManager().set_shutdown_at_application_end()


@pytest.fixture(scope="function")
def dask_client() -> Generator[dd.Client, Any, None]:
    client = dd.Client(n_workers=4, threads_per_worker=4)
    client.forward_logging()
    client.register_plugin(DaskLoggingPlugin(log_level=logging.DEBUG))
    yield client


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: Item, nextitem: Item | None) -> None:
    '''
    This method tries to close a dask client if it is still open. This cannot be done inside
    the 'dask_client' fixture, because the fixture will be called _before_ the auto used
    'setup_shutdown_manager' fixture. This would result in errors since during shutdown
    a lot of dask stuff is done.
    '''
    try:
        client = dd.get_client()
        client.close()
    except Exception:
        pass
