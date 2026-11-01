import logging
from typing import Any, Generator, assert_never, cast

import dask.distributed as dd
import pytest
from _pytest.logging import _LiveLoggingStreamHandler, logging_StreamHandler
from _pytest.nodes import Item
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.dask.init_dask import init_dask
from ecosim_common.tech.dask.shutdown_dask import shutdown_dask_workers
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager

# INIT LOGGER
log_level_during_tests = logging.DEBUG
init_logger(log_level=log_level_during_tests)
pytest_fixture_logger = ESPLogger("PyTestFixture")


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
    # created now, so it does not get a dask event from a client the test closes
    ShutdownManager()
    yield None
    try:
        pytest_fixture_logger.debug("Calling shutdown manager at application end...")
        ShutdownManager().set_shutdown_at_application_end()
        pytest_fixture_logger.debug("Calling shutdown manager at application end...done.")
    finally:
        ShutdownManager.reset_instance()


@pytest.fixture(scope="function")
def dask_client() -> Generator[dd.Client, Any, None]:
    pytest_fixture_logger.info("Creating new distributed dask client")
    client = dd.Client(
        n_workers=4,
        threads_per_worker=4,
    )
    init_dask(
        log_level=log_level_during_tests,
        client=client,
    )
    yield client


@pytest.fixture(
    scope="function",
    params=[CommunicationProtocol.TCP_SOCKET, CommunicationProtocol.DASK],
)
def communication_protocol(request: pytest.FixtureRequest) -> Generator[CommunicationProtocol, Any, None]:
    communication_protocol: CommunicationProtocol = cast(CommunicationProtocol, request.param)
    match communication_protocol:
        case CommunicationProtocol.DASK:
            request.getfixturevalue("dask_client")
        case CommunicationProtocol.TCP_SOCKET:
            pass
        case _:
            assert_never(communication_protocol)

    yield communication_protocol


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: Item, nextitem: Item | None) -> None:
    """
    This method tries to close a dask client if it is still open. This cannot be done inside
    the 'dask_client' fixture, because the fixture will be called _before_ the auto used
    'setup_shutdown_manager' fixture. This would result in errors since during shutdown
    a lot of dask stuff is done.
    """
    # noinspection PyUnusedLocal
    client: dd.Client | None = None
    try:
        client = dd.get_client()
    except Exception:
        pytest_fixture_logger.debug("Dask teardown: failed to get_client -> nothing to do (this is expected behaviour if no dask client is running)")
        return

    if client is None:
        pytest_fixture_logger.debug("Dask teardown: no dask client found -> nothing to do.")
        return

    try:
        pytest_fixture_logger.info("Closing dask client: %s", client)
        for key in client.datasets.keys():
            pytest_fixture_logger.debug("Dask teardown: key in dataset: %s = %s", key, client.get_dataset(key))
        shutdown_dask_workers(client)
        client.close()
        if client.cluster is not None:
            client.cluster.close()
        if dd.client._global_clients is not None:  # noqa: SLF001
            dd.client._global_clients.clear()  # noqa: SLF001
    except Exception as e:
        pytest_fixture_logger.error("Closing dask client failed: %s", e)
    finally:
        # 'shutdown_dask_workers' asks this process for its ShutdownManager, and this hook runs after the
        # fixture that resets it. The manager created here still holds a dask event, so leaving it in place
        # would hand the next test an event whose client is already gone.
        ShutdownManager.reset_instance()
