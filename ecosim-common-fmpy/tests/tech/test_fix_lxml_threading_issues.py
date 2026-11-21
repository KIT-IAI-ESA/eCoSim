from concurrent.futures import ThreadPoolExecutor

from tests.tech.spy_lxml_threading_fix import SpyLxmlThreadingFix


def test_parallel_callers_apply_the_fix_once() -> None:
    lxml_threading_fix = SpyLxmlThreadingFix(delay_in_seconds=0.05)

    with ThreadPoolExecutor(max_workers=8) as executor:
        for _ in range(8):
            executor.submit(lxml_threading_fix.apply_once)

    assert lxml_threading_fix.apply_count == 1
