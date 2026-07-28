import logging
from typing import Any, Generator, assert_never, cast

import dask.distributed as dd
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

pytest_fixture_logger = logging.getLogger("PytestFixtures")


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """runs once before all tests"""
    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def teardown_shutdown_manager() -> Generator[None, None, None]:
    """runs once after all tests"""
    yield
    ShutdownManager().set_shutdown_at_application_end()


@pytest.fixture(scope="function")
def dask_client() -> Generator[dd.Client, Any, None]:
    pytest_fixture_logger.info("Creating new distributed dask client")
    ShutdownManager().reset_instance()
    client = dd.Client(n_workers=4, threads_per_worker=4)
    ShutdownManager().init()
    client.forward_logging()
    client.register_plugin(DaskLoggingPlugin(log_level=logging.DEBUG))
    yield client


@pytest.fixture(
    scope="function",
    # params=[ESPStructureType.SIMPLE, ESPStructureType.DASK_VARIABLE, ESPStructureType.DASK_ACTOR, ESPStructureType.THREAD],
    params=[ESPStructureType.SIMPLE, ESPStructureType.DASK_VARIABLE, ESPStructureType.THREAD],
)
def esp_structure_type(request: pytest.FixtureRequest) -> Generator[ESPStructureType, Any, None]:
    esp_map_type: ESPStructureType = cast(ESPStructureType, request.param)
    match esp_map_type:
        # case ESPStructureType.DASK_ACTOR | ESPStructureType.DASK_VARIABLE:
        #     request.getfixturevalue("dask_client")
        case ESPStructureType.DASK_VARIABLE:
            request.getfixturevalue("dask_client")
        case ESPStructureType.SIMPLE:
            pass
        case ESPStructureType.THREAD:
            pass
        case _:
            assert_never(esp_map_type)

    yield esp_map_type


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
