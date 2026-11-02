import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any
from unittest.mock import Mock

import pytest

from build_docs import NODE_IMAGE, main
from config import REPO_ROOT

DOCS = REPO_ROOT / "docs"
NPM = "/opt/bin/npm"
DOCKER = "/opt/bin/docker"


def install(monkeypatch: pytest.MonkeyPatch, tools: list[str]) -> None:
    monkeypatch.setattr(target=shutil, name="which", value=lambda name: f"/opt/bin/{name}" if name in tools else None)


def after_image(command: list[str]) -> list[str]:
    return command[command.index(NODE_IMAGE) + 1 :]


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    recorded: list[list[str]] = []

    def record(command: list[str], cwd: str, **keywords: Any) -> None:
        assert cwd == str(DOCS)
        recorded.append(command)

    monkeypatch.setattr(target=subprocess, name="run", value=record)
    return recorded


@pytest.mark.parametrize(argnames="arguments", argvalues=[[], ["--npm"]])
def test_npm_runs_what_ci_runs(arguments: list[str], monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    install(monkeypatch=monkeypatch, tools=["npm", "docker"])

    assert main(arguments) == 0

    assert commands == [[NPM, "ci"], [NPM, "run", "build"]]


@pytest.mark.parametrize(argnames=("arguments", "tools"), argvalues=[([], ["docker"]), (["--docker"], ["npm", "docker"])])
def test_docker_runs_what_ci_runs(arguments: list[str], tools: list[str], monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    install(monkeypatch=monkeypatch, tools=tools)

    assert main(arguments) == 0

    assert [command[0] for command in commands] == [DOCKER, DOCKER]
    assert [after_image(command) for command in commands] == [["npm", "ci"], ["npm", "run", "build"]]


def test_docker_mounts_the_docs_folder_as_the_calling_user(monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    install(monkeypatch=monkeypatch, tools=["docker"])
    monkeypatch.setattr(target=os, name="getuid", value=lambda: 1234, raising=False)
    monkeypatch.setattr(target=os, name="getgid", value=lambda: 5678, raising=False)

    assert main(["--docker"]) == 0

    for command in commands:
        rendered = shlex.join(command)
        assert f"{DOCKER} run --rm --init --env TINI_KILL_PROCESS_GROUP=1" in rendered
        assert f"--user 1234:5678 --env HOME=/tmp --volume {DOCS}:/docs --workdir /docs" in rendered


def test_docker_passes_no_user_on_windows(monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    install(monkeypatch=monkeypatch, tools=["docker"])
    monkeypatch.setattr(target=sys, name="platform", value="win32")

    assert main(["--docker"]) == 0

    assert all("--user" not in command for command in commands)


def test_node_image_is_pinned_to_the_major_version_of_ci() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    major_version = re.search(pattern=r"node-version: (\d+)", string=workflow)

    assert major_version is not None
    assert re.fullmatch(pattern=rf"node:{major_version[1]}\.\d+\.\d+-[a-z-]+", string=NODE_IMAGE)


@pytest.mark.parametrize(
    argnames=("arguments", "tools", "message"),
    argvalues=[
        ([], [], "Neither npm nor docker is on PATH"),
        (["--npm"], [], "Neither npm nor docker is on PATH"),
        (["--docker"], [], "Neither npm nor docker is on PATH"),
        (["--docker"], ["npm"], "docker is not on PATH, but npm is. Install docker, or use --npm."),
        (["--npm"], ["docker"], "npm is not on PATH, but docker is. Install npm, or use --docker."),
    ],
)
def test_a_missing_tool_is_a_clear_error(
    arguments: list[str],
    tools: list[str],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    commands: list[list[str]],
) -> None:
    install(monkeypatch=monkeypatch, tools=tools)

    assert main(arguments) == 1

    assert message in capsys.readouterr().err
    assert commands == []


def test_a_failing_step_stops_the_build_and_returns_its_exit_code(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    failing_run = Mock(side_effect=subprocess.CalledProcessError(returncode=3, cmd=[NPM, "ci"]))
    install(monkeypatch=monkeypatch, tools=["npm"])
    monkeypatch.setattr(target=subprocess, name="run", value=failing_run)

    assert main([]) == 3

    failing_run.assert_called_once()
    assert f"exit code 3: {NPM} ci" in capsys.readouterr().err


def test_serve_with_npm_starts_the_server_instead_of_building(monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    install(monkeypatch=monkeypatch, tools=["npm"])

    assert main(["--serve"]) == 0

    assert commands == [[NPM, "ci"], [NPM, "start"]]


def test_serve_with_docker_is_reachable_from_this_machine_only(monkeypatch: pytest.MonkeyPatch, commands: list[list[str]]) -> None:
    install(monkeypatch=monkeypatch, tools=["docker"])

    assert main(["--docker", "--serve"]) == 0

    install_step, serve_step = commands
    assert "--publish" not in install_step
    assert "--publish 127.0.0.1:3000:3000" in shlex.join(serve_step)
    assert after_image(serve_step) == ["npm", "start", "--", "--host", "0.0.0.0", "--no-open"]


def test_stopping_the_server_is_not_a_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch=monkeypatch, tools=["npm"])
    monkeypatch.setattr(target=subprocess, name="run", value=Mock(side_effect=KeyboardInterrupt))

    assert main(["--serve"]) == 130
