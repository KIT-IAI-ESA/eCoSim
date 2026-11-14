from ecosim_common_fmpy.tech.fmu_platforms import binary_platforms
from ecosim_test_common.resources.resource_utils import fmu2_model_path


def test_the_binary_platforms_of_an_fmu_leave_out_its_c_sources() -> None:
    assert binary_platforms(fmu_file=fmu2_model_path()) == ["darwin64", "linux64", "win32", "win64"]
