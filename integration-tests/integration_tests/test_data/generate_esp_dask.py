from ecosim_common.communication.dask.esp_dask import ESPDask
from ecosim_common.tech.parallel.parallel_lock import ParallelLock

_test_esp_dask: ESPDask | None = None
_create_lock: ParallelLock = ParallelLock.dask()


# TODO_OSR: common abstraction between ESPSocket and ESPDask
def get_test_esp_dask() -> ESPDask:
    global _test_esp_dask
    if _test_esp_dask is not None:
        return _test_esp_dask
    with _create_lock:
        if _test_esp_dask is None:
            _test_esp_dask = ESPDask("TEST_DASK_ID")
            _test_esp_dask.connect()
        # noinspection PyTypeChecker
        return _test_esp_dask
