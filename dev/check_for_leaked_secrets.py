#!/usr/bin/env python3
"""Scans the whole git history of every branch for leaked secrets.

The pre-commit hook 'betterleaks' only scans the staged changes; this runs its manual-stage
variants from .pre-commit-config.yaml, which scan all commits.
"""

import argparse
import json
import subprocess
import sys
from typing import Any, Dict, List, Sequence

from config import REPO_ROOT, get_uv_path, subproject_environment

CHECK_HOOK = "betterleaks-full-history"
REPORT_HOOK = "betterleaks-with-unredacted-report"
# written by the report hook, see its entry in .pre-commit-config.yaml
REPORT_PATH = REPO_ROOT / ".betterleaks-report.json"
# the default ignore file, read by betterleaks from the repository root on every scan
KNOWN_LEAKS_PATH = REPO_ROOT / ".betterleaksignore"
INTERACTIVE_UPDATE = "--interactive-update-known-leaks"
ADD, SKIP, QUIT = "a", "s", "q"

Leak = Dict[str, Any]


def run_precommit_hook(hook: str) -> int:
    # --verbose shows the findings summary even when nothing leaked
    command = [get_uv_path(), "run", "pre-commit", "run", hook, "--hook-stage=manual", "--all-files", "--verbose"]
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=str(REPO_ROOT), env=subproject_environment()).returncode


def find_new_leaks() -> List[Leak]:
    run_precommit_hook(REPORT_HOOK)
    try:
        return list(json.loads(REPORT_PATH.read_text(encoding="utf-8")))
    finally:
        REPORT_PATH.unlink(missing_ok=True)


def add_to_known_leaks(leaks: List[Leak]) -> None:
    known_leaks = KNOWN_LEAKS_PATH.read_text(encoding="utf-8").splitlines() if KNOWN_LEAKS_PATH.exists() else []
    new_leaks = [leak["Fingerprint"] for leak in leaks]
    KNOWN_LEAKS_PATH.write_text("".join(f"{line}\n" for line in known_leaks + new_leaks), encoding="utf-8")
    print(f"added {len(new_leaks)} leaks to {KNOWN_LEAKS_PATH.name}")


def describe_leak(leak: Leak, number: int, total: int) -> str:
    return (
        f"\n[{number}/{total}] {leak['RuleID']}: {leak['Description']}\n"
        f"  file:   {leak['File']}:{leak['StartLine']}\n"
        f"  commit: {leak['Commit'][:12]} {leak['Date']} {leak['Author']}\n"
        f"  match:  {leak['Match']}\n"
        f"  secret: {leak['Secret']}"
    )


def ask_leak_handling(leak: Leak, number: int, total: int) -> str:
    print(describe_leak(leak, number, total))
    answer = ""
    while answer not in (ADD, SKIP, QUIT):
        try:
            answer = input(f"[{ADD}]dd to known leaks, [{SKIP}]kip, [{QUIT}]uit: ").strip().lower()
        except EOFError:
            answer = QUIT
    return answer


def review_leaks(leaks: List[Leak]) -> List[Leak]:
    accepted: List[Leak] = []
    for number, leak in enumerate(leaks, start=1):
        answer = ask_leak_handling(leak, number, len(leaks))
        if answer == QUIT:
            break
        if answer == ADD:
            accepted.append(leak)
    return accepted


def interactively_update_known_leaks() -> int:
    add_to_known_leaks(review_leaks(find_new_leaks()))
    return 0


def run_history_check() -> int:
    return_code = run_precommit_hook(CHECK_HOOK)
    if return_code != 0:
        print(f"\nTo store findings as known in {KNOWN_LEAKS_PATH.name}, run this script with {INTERACTIVE_UPDATE}")
    return return_code


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(INTERACTIVE_UPDATE, action="store_true", help=f"ask for every new leak whether to store it in {KNOWN_LEAKS_PATH.name}")
    arguments = parser.parse_args(argv)
    return interactively_update_known_leaks() if arguments.interactive_update_known_leaks else run_history_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
