from pathlib import Path


def integration_test_resource_path() -> Path:
    return Path(__file__).parent.parent / "resources"


def performance_data_resource_path() -> Path:
    return integration_test_resource_path() / "performance"
