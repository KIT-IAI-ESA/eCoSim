import zipfile
from pathlib import Path

from ecosim_test_common.resources.resource_utils import fmu3_model_path


class StateSpaceSimulationData:
    @staticmethod
    def fmu_file_with_fixed_dimension(
        directory: Path,
        value_reference: int,
        start: int,
    ) -> Path:
        """Copy of the StateSpace FMU whose dimensions sized by `value_reference` have the fixed size `start`."""
        fmu_file = directory / fmu3_model_path().name
        with zipfile.ZipFile(fmu3_model_path()) as source, zipfile.ZipFile(fmu_file, mode="w") as target:
            for entry in source.infolist():
                data = source.read(entry)
                if entry.filename == "modelDescription.xml":
                    data = data.replace(f'<Dimension valueReference="{value_reference}"/>'.encode(), f'<Dimension start="{start}"/>'.encode())
                target.writestr(zinfo_or_arcname=entry, data=data)
        return fmu_file
