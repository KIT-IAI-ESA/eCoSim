import re
import zipfile
from pathlib import Path


def generate_fmu_without_co_simulation(fmu_file: Path, directory: Path) -> Path:
    # the element is <CoSimulation .../> or has a closing tag
    model_description, removed_count = re.subn(
        pattern=rb"<CoSimulation\b[^>]*/>|<CoSimulation\b.*?</CoSimulation>",
        repl=b"",
        string=_model_description(fmu_file=fmu_file),
        count=1,
        flags=re.DOTALL,
    )
    if removed_count == 0:
        raise ValueError(f"{fmu_file} has no CoSimulation element")
    return _copy_with(fmu_file=fmu_file, target=directory / fmu_file.name, model_description=model_description)


def generate_fmu_without_binaries_for(fmu_file: Path, directory: Path, platform: str) -> Path:
    """Copy of the FMU without its binary for the platform, like linux64."""
    target = directory / fmu_file.name
    with zipfile.ZipFile(fmu_file) as source, zipfile.ZipFile(target, mode="w") as copy:
        for entry in source.infolist():
            if not entry.filename.startswith(f"binaries/{platform}/"):
                copy.writestr(zinfo_or_arcname=entry, data=source.read(entry))
    return target


def generate_fmi1_fmu(directory: Path) -> Path:
    """Writes an FMI 1.0 FMU with one input and no binary."""
    model_description = """<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription fmiVersion="1.0" modelName="old" modelIdentifier="old" guid="{0}" numberOfContinuousStates="0" numberOfEventIndicators="0">
  <ModelVariables>
    <ScalarVariable name="u" valueReference="0" causality="input"><Real start="0"/></ScalarVariable>
  </ModelVariables>
  <Implementation><CoSimulation_StandAlone><Capabilities/></CoSimulation_StandAlone></Implementation>
</fmiModelDescription>
"""
    fmu_file = directory / "old.fmu"
    with zipfile.ZipFile(fmu_file, mode="w") as fmu:
        fmu.writestr(zinfo_or_arcname="modelDescription.xml", data=model_description)
    return fmu_file


def _model_description(fmu_file: Path) -> bytes:
    with zipfile.ZipFile(fmu_file) as source:
        return source.read("modelDescription.xml")


def _copy_with(fmu_file: Path, target: Path, model_description: bytes) -> Path:
    with zipfile.ZipFile(fmu_file) as source, zipfile.ZipFile(target, mode="w") as copy:
        for entry in source.infolist():
            copy.writestr(zinfo_or_arcname=entry, data=model_description if entry.filename == "modelDescription.xml" else source.read(entry))
    return target
