#!/usr/bin/env python3
"""Build the eCoSim container images of dev/docker/compose.yaml, with docker or podman.

Usage: python dev/build_docker_images.py [IMAGE ...]
"""

import argparse
import shutil
import subprocess

import sys

from config import REPO_ROOT, error_print, run

COMPOSE_FILE = REPO_ROOT / "dev" / "docker" / "compose.yaml"
TOOLS = ("docker", "podman")
INTERRUPTED_EXIT_CODE = 130


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Build the container images of {COMPOSE_FILE.relative_to(REPO_ROOT)}.")
    parser.add_argument(
        "images",
        metavar="IMAGE",
        nargs="*",
        help="The services to build, like ecosim-server or ecosim-client-fmu-v2. Default: all.",
    )
    return parser.parse_args(arguments)


def find_container_tool() -> str | None:
    return next((path for tool in TOOLS if (path := shutil.which(tool))), None)


def build_docker_images(tool: str, images: list[str]) -> int:
    try:
        run(cmd=[tool, "compose", "--file", str(COMPOSE_FILE), "build", *images], cwd=REPO_ROOT)
    except subprocess.CalledProcessError as error:
        error_print(f"Building the images failed with exit code {error.returncode}.")
        return error.returncode
    except KeyboardInterrupt:
        return INTERRUPTED_EXIT_CODE
    return 0


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    tool = find_container_tool()
    if tool is None:
        error_print(f"No tool for creating images is on PATH. Install one of them to build the images: {TOOLS}")
        return 1
    return build_docker_images(tool=tool, images=options.images)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
