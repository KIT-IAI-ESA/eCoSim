#!/usr/bin/env python3
"""Build the documentation the way CI does, with npm or in a Node container.

Usage: python dev/build_docs.py [--npm | --docker] [--serve]
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys

from config import REPO_ROOT, error_print, run

DOCS_DIRECTORY = REPO_ROOT / "docs"
CONTAINER_DIRECTORY = "/docs"
# keep major version in step with .github/workflows/docs.yml
NODE_IMAGE = "node:20.20.2-bookworm-slim"
SERVE_PORT = 3000
INTERRUPTED_EXIT_CODE = 130


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the documentation into docs/build the way CI does.")
    tool = parser.add_mutually_exclusive_group()
    tool.add_argument("--npm", action="store_const", const="npm", dest="tool", help="Use the installed npm.")
    tool.add_argument("--docker", action="store_const", const="docker", dest="tool", help=f"Use npm inside {NODE_IMAGE}.")
    parser.add_argument("--serve", action="store_true", help=f"Serve with live reload on port {SERVE_PORT} instead of building.")
    return parser.parse_args(arguments)


def choose_tool(requested: str | None, available: list[str]) -> str | None:
    if not available:
        error_print("Neither npm nor docker is on PATH. Install Node.js 20 or Docker to build the documentation.")
        return None
    if requested is None or requested in available:
        return requested or available[0]
    error_print(f"{requested} is not on PATH, but {available[0]} is. Install {requested}, or use --{available[0]}.")
    return None


def npm_commands(executable: str, serve: bool) -> list[list[str]]:
    return [[executable, "ci"], [executable, "start"] if serve else [executable, "run", "build"]]


def user_arguments() -> list[str]:
    # Docker Desktop on Windows already gives bind-mounted files to the calling user
    if sys.platform == "win32":
        return []
    return ["--user", f"{os.getuid()}:{os.getgid()}"]


def docker_commands(executable: str, serve: bool) -> list[list[str]]:
    # Without the process group, Ctrl+C stops npm but not the server it started
    container = [executable, "run", "--rm", "--init", "--env", "TINI_KILL_PROCESS_GROUP=1", *user_arguments()]
    # The calling user may have no writable home in the image
    container += ["--env", "HOME=/tmp", "--volume", f"{DOCS_DIRECTORY}:{CONTAINER_DIRECTORY}", "--workdir", CONTAINER_DIRECTORY]
    install = [*container, NODE_IMAGE, "npm", "ci"]
    if not serve:
        return [install, [*container, NODE_IMAGE, "npm", "run", "build"]]
    publish = ["--publish", f"127.0.0.1:{SERVE_PORT}:{SERVE_PORT}"]
    return [install, [*container, *publish, NODE_IMAGE, "npm", "start", "--", "--host", "0.0.0.0", "--no-open"]]


COMMANDS = {"npm": npm_commands, "docker": docker_commands}


def run_commands(commands: list[list[str]]) -> int:
    try:
        for command in commands:
            run(cmd=command, cwd=DOCS_DIRECTORY)
    except subprocess.CalledProcessError as error:
        error_print(f"Failed with exit code {error.returncode}: {shlex.join(error.cmd)}")
        return error.returncode
    except KeyboardInterrupt:
        return INTERRUPTED_EXIT_CODE
    return 0


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    paths = {tool: path for tool in COMMANDS if (path := shutil.which(tool))}
    tool = choose_tool(requested=options.tool, available=list(paths))
    if tool is None:
        return 1
    return run_commands(COMMANDS[tool](executable=paths[tool], serve=options.serve))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
