from pathlib import Path
from zipfile import ZipFile

from ecosim_test_common.fmpy_platform import FMPyPlatform

X86_64_LINUX = FMPyPlatform(platform="linux64", platform_tuple="x86_64-linux", shared_library_extension=".so")
AARCH64_LINUX = FMPyPlatform(platform="linux64", platform_tuple="aarch64-linux", shared_library_extension=".so")


def _write_fmu(directory: Path, fmi_version: str, binaries: list[str]) -> Path:
    fmu_file = directory / "Model.fmu"
    with ZipFile(fmu_file, "w") as fmu:
        fmu.writestr(
            "modelDescription.xml",
            f'<fmiModelDescription fmiVersion="{fmi_version}"><CoSimulation modelIdentifier="Model"/><ModelVariables/></fmiModelDescription>',
        )
        for binary in binaries:
            fmu.writestr(binary, "")
    return fmu_file


def test_an_fmi2_binary_for_linux64_is_loaded_on_x86_64_linux_only(tmp_path: Path) -> None:
    fmu_file = _write_fmu(directory=tmp_path, fmi_version="2.0", binaries=["binaries/linux64/Model.so"])
    x86_64_windows = FMPyPlatform(platform="win64", platform_tuple="x86_64-windows", shared_library_extension=".dll")

    assert X86_64_LINUX.loads_binary_of(fmu_file)
    # fmpy looks into linux64 on arm64 Linux, too
    assert not AARCH64_LINUX.loads_binary_of(fmu_file)
    assert not x86_64_windows.loads_binary_of(fmu_file)


def test_an_fmi2_binary_for_aarch64_linux_is_not_loaded(tmp_path: Path) -> None:
    fmu_file = _write_fmu(directory=tmp_path, fmi_version="2.0", binaries=["binaries/aarch64-linux/Model.so"])

    assert not AARCH64_LINUX.loads_binary_of(fmu_file)


def test_an_fmi3_binary_for_aarch64_linux_is_loaded_on_aarch64_linux_only(tmp_path: Path) -> None:
    fmu_file = _write_fmu(directory=tmp_path, fmi_version="3.0", binaries=["binaries/aarch64-linux/Model.so"])

    assert AARCH64_LINUX.loads_binary_of(fmu_file)
    assert not X86_64_LINUX.loads_binary_of(fmu_file)
