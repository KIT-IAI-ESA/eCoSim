import itertools
import shutil
import subprocess
from unittest.mock import Mock

import pytest

from config import SUBPROJECTS
from sync_projects import main

UV = "/opt/bin/uv"
PROJECTS_AND_ROOT = len(SUBPROJECTS) + 1


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch) -> Mock:
    monkeypatch.setattr(target=shutil, name="which", value=lambda name: UV)
    fake_run = Mock()
    monkeypatch.setattr(target=subprocess, name="run", value=fake_run)
    return fake_run


def sync_commands(run: Mock) -> list[list[str]]:
    return [call.args[0] for call in run.call_args_list if call.args[0][1] == "sync"]


def test_syncs_without_checking_the_locks_by_default(run: Mock) -> None:
    assert main([]) == 0

    commands = sync_commands(run)
    assert len(commands) == PROJECTS_AND_ROOT
    assert all("--locked" not in command for command in commands)


def test_locked_checks_the_lock_of_every_project(run: Mock) -> None:
    assert main(["--locked"]) == 0

    commands = sync_commands(run)
    assert len(commands) == PROJECTS_AND_ROOT
    assert all("--locked" in command for command in commands)


def test_a_failed_project_does_not_stop_the_others_but_fails_the_run(run: Mock) -> None:
    # only the first command fails, the venv of the first project
    run.side_effect = itertools.chain([subprocess.CalledProcessError(returncode=1, cmd=[UV, "venv", "--clear"])], itertools.repeat(None))

    assert main(["--locked"]) == 1

    assert len(sync_commands(run)) == PROJECTS_AND_ROOT - 1
