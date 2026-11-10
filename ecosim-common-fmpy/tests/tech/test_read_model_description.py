from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import Barrier

import pytest
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu
from fmpy.model_description import ValidationError

from tests.tech.spy_lxml_threading_fix import SpyLxmlThreadingFix


def _model_name_after(fmu_file: Path, start: Barrier) -> str:
    start.wait()
    # the schema validation is where lxml races
    return read_model_description(file=fmu_file, validate=True).modelName


def test_parallel_reads_with_schema_validation_succeed() -> None:
    fmu_files = [fmu2_model_path(), fmu3_model_path()] * 8
    start = Barrier(parties=len(fmu_files))

    with ThreadPoolExecutor(max_workers=len(fmu_files)) as executor:
        model_names = list(executor.map(partial(_model_name_after, start=start), fmu_files))

    assert model_names == ["Feedthrough", "StateSpace"] * 8


def test_reading_applies_the_lxml_fix_before_the_read(tmp_path: Path) -> None:
    lxml_threading_fix = SpyLxmlThreadingFix()

    with pytest.raises(FileNotFoundError):
        read_model_description(file=tmp_path / "missing.fmu", lxml_threading_fix=lxml_threading_fix)

    assert lxml_threading_fix.apply_count == 1


def test_reading_skips_the_schema_validation(tmp_path: Path) -> None:
    broken_fmu_file = generate_broken_fmu(fmu_file=fmu2_model_path(), directory=tmp_path)

    assert read_model_description(file=broken_fmu_file).modelName == "Feedthrough"


def test_reading_with_validation_rejects_a_model_description_that_fails_the_schema(tmp_path: Path) -> None:
    broken_fmu_file = generate_broken_fmu(fmu_file=fmu2_model_path(), directory=tmp_path)

    with pytest.raises(ValidationError):
        read_model_description(file=broken_fmu_file, validate=True)
