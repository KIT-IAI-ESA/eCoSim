import shutil

import pytest

from init_dev import main


def test_stops_and_points_to_the_official_installer_without_uv(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(target=shutil, name="which", value=lambda name: None)

    assert main(["--dry-run"]) == 1

    captured = capsys.readouterr()
    assert "https://docs.astral.sh/uv/getting-started/installation/" in captured.err
    assert "uv sync" not in captured.out


def test_neither_installs_uv_nor_updates_the_hooks(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(target=shutil, name="which", value=lambda name: f"/opt/bin/{name}")

    assert main(["--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "/opt/bin/uv sync" in output
    assert "/opt/bin/uv run pre-commit install" in output
    assert "pip" not in output
    assert "autoupdate" not in output
