from concurrent.futures import ThreadPoolExecutor

from ecosim_common_fmpy.tech.fix_lmxl_threading_issues import LxmlThreadingFix

from tests.tech.counting_lxml_fix import CountingLxmlFix


def test_parallel_callers_apply_the_fix_once() -> None:
    fix = CountingLxmlFix(delay_in_seconds=0.05)
    lxml_threading_fix = LxmlThreadingFix(fix=fix)

    with ThreadPoolExecutor(max_workers=8) as executor:
        for _ in range(8):
            executor.submit(lxml_threading_fix.apply_once)

    assert fix.call_count == 1
