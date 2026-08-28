from pathlib import Path


def production_source_path() -> Path:
    return Path(__file__).parent.parent.parent / "ecosim_client_fmu_v2"
