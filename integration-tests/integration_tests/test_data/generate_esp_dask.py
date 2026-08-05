from ecosim_common.communication.dask.esp_dask import ESPDask


# TODO_OSR: common abstraction between ESPSocket and ESPDask
def generate_esp_dask() -> ESPDask:
    _test_esp_dask = ESPDask("TEST_DASK_ID")
    _test_esp_dask.connect()
    return _test_esp_dask
