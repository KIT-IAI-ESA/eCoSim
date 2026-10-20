#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path

TYPES = ("feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert")
TITLE = re.compile(r"^(\w+)(\([^()]+\))?!?: \S")
GENERATED_PREFIXES = ("Merge ", 'Revert "')


def message_lines(message: str) -> list[str]:
    lines = [line.rstrip() for line in message.splitlines() if not line.startswith("#")]
    return "\n".join(lines).strip().splitlines()


def find_errors(message: str) -> list[str]:
    lines = message_lines(message) or [""]
    if lines[0].startswith(GENERATED_PREFIXES):
        return []
    errors = title_errors(lines[0])
    if len(lines) > 1 and lines[1]:
        errors.append("add a blank line after the first line")
    return errors


def title_errors(title: str) -> list[str]:
    match = TITLE.match(title)
    if not match:
        return ["first line must look like '<type>: <summary>' or '<type>(<scope>): <summary>'"]
    if match[1] not in TYPES:
        return [f"unknown type '{match[1]}', use one of: {', '.join(TYPES)}"]
    return []


def commit_messages(revisions: list[str]) -> dict[str, str]:
    log = subprocess.run(["git", "log", "--format=%h %s%x00%B%x01", *revisions], capture_output=True, text=True, check=True).stdout
    entries = (entry.lstrip("\n").split("\x00", 1) for entry in log.split("\x01") if entry.strip())
    return {f"commit {title}": message for title, message in entries}


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check commit messages, see docs/dev/developing.md")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("file", nargs="?", type=Path)
    source.add_argument("--revisions", nargs="+")
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    messages = commit_messages(options.revisions) if options.revisions else {"commit message": options.file.read_text(encoding="utf-8")}
    failures = {name: errors for name, message in messages.items() if (errors := find_errors(message))}
    for name, errors in failures.items():
        print(f"{name}:", *(f"  - {error}" for error in errors), sep="\n", file=sys.stderr)
    if failures:
        print("format: <type>[(<scope>)][!]: <summary>, see docs/dev/developing.md", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
