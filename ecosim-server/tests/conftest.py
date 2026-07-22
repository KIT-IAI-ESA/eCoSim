import logging
from typing import Any, Generator, assert_never, cast

import dask.distributed
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager

# INIT LOGGER
init_logger(log_level=logging.DEBUG)
pytest_fixture_logger = ESPLogger("PyTestFixture")


@pytest.fixture(scope="function", autouse=True)
def setup_shutdown_manager() -> Generator[None, Any, None]:
    pytest_fixture_logger.debug("Initializing shutdown manager")
    ShutdownManager().init()
    yield None
    ShutdownManager().set_shutdown_at_application_end()
    pytest_fixture_logger.debug("Called shutdown manager at application end")
    ShutdownManager.reset_instance()


@pytest.fixture(scope="function")
def dask_client() -> Generator[dask.distributed.Client, Any, None]:
    pytest_fixture_logger.info("Creating new distributed dask client")
    ShutdownManager().reset_instance()
    client = dask.distributed.Client(n_workers=4, threads_per_worker=4)
    ShutdownManager().init()
    client.forward_logging()
    client.register_plugin(DaskLoggingPlugin(log_level=logging.DEBUG))
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
