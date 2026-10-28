from unittest.mock import MagicMock

import pytest
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config

from tests.client.never_started_client import NeverStartedClient


def test_shutdown_of_a_never_connected_client_does_nothing() -> None:
    client = NeverStartedClient(_client_config=generate_mocked_client_config())

    client.on_app_shutdown()

    assert client._channel_or_none is None  # noqa: SLF001


def test_shutdown_closes_the_channel_of_a_connected_client() -> None:
    client = NeverStartedClient(
        _client_config=generate_mocked_client_config(),
        _channel_or_none=MagicMock(),
    )

    client.on_app_shutdown()

    client._channel.close.assert_called_once()  # type: ignore[attr-defined]  # noqa: SLF001


def test_a_subclass_logs_under_its_own_name(caplog: pytest.LogCaptureFixture) -> None:
    client = NeverStartedClient(_client_config=generate_mocked_client_config())

    client.logger.warning("hello")

    assert [record.name for record in caplog.records] == ["NeverStartedClient"]
