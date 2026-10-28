import pytest
from unittest.mock import MagicMock

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from tests.client.never_started_client import NeverStartedClient


def _client_config() -> ClientConfig:
    client_config = MagicMock(spec=ClientConfig)
    client_config.communication_protocol.return_value = CommunicationProtocol.TCP_SOCKET
    return client_config


def test_shutdown_of_a_never_connected_client_does_nothing() -> None:
    client = NeverStartedClient(_client_config=_client_config())

    client.on_app_shutdown()

    assert client._channel_or_none is None  # noqa: SLF001


def test_shutdown_closes_the_channel_of_a_connected_client() -> None:
    client = NeverStartedClient(_client_config=_client_config(), _channel_or_none=MagicMock())

    client.on_app_shutdown()

    client._channel.close.assert_called_once()  # type: ignore[attr-defined]  # noqa: SLF001


def test_a_subclass_logs_under_its_own_name(caplog: pytest.LogCaptureFixture) -> None:
    client = NeverStartedClient(_client_config=_client_config())

    client.logger.warning("hello")

    assert [record.name for record in caplog.records] == ["NeverStartedClient"]
