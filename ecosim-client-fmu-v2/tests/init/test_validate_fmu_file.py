import subprocess
import sys

from tests.tech import resource_utils


def test_validate_fmu_file_happy_path() -> None:
    main_file = f"{resource_utils.production_source_path().absolute()}/main.py"
    config_file = f"{resource_utils.resource_path().absolute()}/models/house/linux/heating_preferences_linux.ini"
    print("")
    print(f"Main file: {main_file}")
    print(f"Config file: {config_file}")
    proc = subprocess.Popen(
        [sys.executable, "-u", main_file, "--debug", "--validate-fmu-file-only", "--config-file", config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        out, err = proc.communicate(timeout=50)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    print("OUT:", out)
    print("ERR:", err)

    assert 0 == proc.returncode


def test_validate_fmu_file_with_error() -> None:
    main_file = f"{resource_utils.production_source_path().absolute()}/main.py"
    config_file = f"{resource_utils.resource_path().absolute()}/models/house/linux/heating_broken_preferences_linux.ini"
    print("")
    print(f"Main file: {main_file}")
    print(f"Config file: {config_file}")
    proc = subprocess.Popen(
        [sys.executable, "-u", main_file, "--debug", "--validate-fmu-file-only", "--config-file", config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        out, err = proc.communicate(timeout=50)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    print("OUT:", out)
    print("ERR:", err)

    assert 0 != proc.returncode
