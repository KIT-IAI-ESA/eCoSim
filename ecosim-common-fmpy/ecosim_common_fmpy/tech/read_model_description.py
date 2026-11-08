from pathlib import Path

import fmpy
from fmpy.model_description import ModelDescription

from ecosim_common_fmpy.tech.fix_lmxl_threading_issues import PROCESS_LXML_THREADING_FIX, LxmlThreadingFix


def read_model_description(
    file: str | Path,
    validate: bool = False,
    lxml_threading_fix: LxmlThreadingFix = PROCESS_LXML_THREADING_FIX,
) -> ModelDescription:
    lxml_threading_fix.apply_once()
    return fmpy.read_model_description(filename=str(file), validate=validate)
