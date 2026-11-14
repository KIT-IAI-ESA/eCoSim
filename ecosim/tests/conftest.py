import pytest


@pytest.fixture(autouse=True)
def started_without_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    """The printed commands start with ecosim, also when uv run started the tests."""
    monkeypatch.delenv("UV", raising=False)
