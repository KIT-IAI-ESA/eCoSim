#!/usr/bin/env python3
import sys
import re
from pathlib import Path

SNAKE_CASE_REGEX = re.compile(r"^[a-z_][a-z0-9_]*\.py$")
IGNORED_FILENAMES: set[str] = set()


def main() -> None:
    has_error = False
    filepaths = sys.argv[1:]
    for filepath in filepaths:
        filename = Path(filepath).name
        if filename in IGNORED_FILENAMES:
            continue
        if not SNAKE_CASE_REGEX.match(filename):
            print(
                f"FAIL: Invalid Python filename '{filepath}'. "
                "Must be snake_case (e.g., 'my_module.py').",
                file=sys.stderr,
            )
            has_error = True

    if has_error:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
