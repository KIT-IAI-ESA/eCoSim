import zipfile
from pathlib import Path


def generate_broken_fmu(
    fmu_file: Path,
    directory: Path,
    model_description_entry: str = "modelDescription.xml",
) -> Path:
    """Copy of the FMU with a model description that fails the schema check."""
    broken_fmu_file = directory / fmu_file.name
    with zipfile.ZipFile(fmu_file) as source, zipfile.ZipFile(broken_fmu_file, mode="w") as target:
        for entry in source.infolist():
            if entry.filename != "modelDescription.xml":
                target.writestr(zinfo_or_arcname=entry, data=source.read(entry))
        model_description = source.read("modelDescription.xml").replace(b"<CoSimulation", b"<UnknownElement/><CoSimulation", 1)
        target.writestr(zinfo_or_arcname=model_description_entry, data=model_description)
    return broken_fmu_file
