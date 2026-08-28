"""
Every worker logs through its own handler. Forwarding those records to the client on top of that
printed each of them twice - the worker's handler wrote it, the client re-emitted it through the
logger of the same name, and under SLURM both streams land in the same output file.
"""

import logging
from typing import cast
from unittest.mock import MagicMock

import pytest
from distributed import Client
from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.dask.init_dask import init_dask
from pytest_mock import MockerFixture


@pytest.fixture
def dask_client_spy() -> MagicMock:
    return MagicMock()


def _init_dask_with(dask_client_spy: MagicMock) -> None:
    init_dask(log_level=logging.DEBUG, client=cast(Client, dask_client_spy))


def test_init_dask_does_not_forward_the_worker_logging(dask_client_spy: MagicMock) -> None:
    _init_dask_with(dask_client_spy)
    dask_client_spy.forward_logging.assert_not_called()


def test_init_dask_lets_every_worker_set_up_its_own_logging(dask_client_spy: MagicMock) -> None:
    _init_dask_with(dask_client_spy)
    registered = [call.args[0] for call in dask_client_spy.register_plugin.call_args_list]
    assert any(isinstance(plugin, DaskLoggingPlugin) for plugin in registered)


def test_init_dask_sets_up_the_worker_logging_only_once(dask_client_spy: MagicMock) -> None:
    _init_dask_with(dask_client_spy)
    run_functions = [call.args[0].__name__ for call in dask_client_spy.run.call_args_list]
    assert not any("logger" in name for name in run_functions)


def test_the_logging_plugin_initializes_the_logger_of_its_worker(mocker: MockerFixture) -> None:
    init_logger = mocker.patch("ecosim_common.communication.dask.dask_logging_plugin.init_logger")
    DaskLoggingPlugin(log_level=logging.DEBUG).setup(worker=mocker.MagicMock())
    init_logger.assert_called_once_with(logging.DEBUG)
