from pathlib import Path


def create_files(folder: Path, *file_names: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for file_name in file_names:
        (folder / file_name).touch()
