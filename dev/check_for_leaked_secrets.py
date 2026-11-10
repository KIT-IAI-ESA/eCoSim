#!/usr/bin/env python3
"""Scans the whole git history of every branch for leaked secrets.

The pre-commit hook 'betterleaks' only scans the staged changes; this runs its manual-stage
variants from .pre-commit-config.yaml, which scan all commits.
"""

import argparse
import json
import subprocess
import sys
from typing import List, Sequence

from config import REPO_ROOT, get_uv_path, subproject_environment

CHECK_HOOK = "betterleaks-history"
REPORT_HOOK = "betterleaks-known-leaks"
# written by the report hook, see its entry in .pre-commit-config.yaml
REPORT = REPO_ROOT / ".betterleaks-report.json"
# the default ignore file, read by betterleaks from the repository root on every scan
KNOWN_LEAKS = REPO_ROOT / ".betterleaksignore"
AUTO_UPDATE = "--auto-update-known-leaks"


def run_precommit_hook(hook: str) -> int:
    # --verbose shows the findings summary even when nothing leaked
    command = [get_uv_path(), "run", "pre-commit", "run", hook, "--hook-stage=manual", "--all-files", "--verbose"]
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=str(REPO_ROOT), env=subproject_environment()).returncode


def read_and_delete_report() -> List[str]:
    try:
        return [finding["Fingerprint"] for finding in json.loads(REPORT.read_text(encoding="utf-8"))]
    finally:
        REPORT.unlink(missing_ok=True)


def find_and_update_known_leaks() -> int:
    run_precommit_hook(REPORT_HOOK)
    new_leaks = read_and_delete_report()
    known_leaks = KNOWN_LEAKS.read_text(encoding="utf-8").splitlines() if KNOWN_LEAKS.exists() else []
    KNOWN_LEAKS.write_text("".join(f"{line}\n" for line in known_leaks + new_leaks), encoding="utf-8")
    print(f"added {len(new_leaks)} leaks to {KNOWN_LEAKS.name}")
    return 0


def run_history_check() -> int:
    return_code = run_precommit_hook(CHECK_HOOK)
    if return_code != 0:
        print(f"\nTo accept all findings as known, store them in {KNOWN_LEAKS.name}: run this script with {AUTO_UPDATE}")
    return return_code


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(AUTO_UPDATE, action="store_true", help=f"store every leak of the history in {KNOWN_LEAKS.name}")
    arguments = parser.parse_args(argv)
    return find_and_update_known_leaks() if arguments.auto_update_known_leaks else run_history_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
