#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Error: Directory argument required", file=sys.stderr)
    sys.exit(1)

target_dir = Path(__file__).parent.parent / sys.argv[1]

if not target_dir.exists():
    print(f"Error: Directory '{target_dir}' does not exist", file=sys.stderr)
    sys.exit(1)

os.chdir(target_dir)
print(f"INFO: running mypy in {target_dir}", file=sys.stdout)
sys.exit(subprocess.call(["uv", "run", "mypy", "."]))
