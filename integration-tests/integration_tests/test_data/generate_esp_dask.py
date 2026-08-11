from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.dask.dask_channel import DaskChannel


# TODO_OSR: common abstraction between ESPSocket and ESPDask
def generate_dask_channel() -> DaskChannel:
    _test_esp_dask = DaskChannel(
        _connection_address=ConnectionAddress(ip="localhost", port=8786),
        _internal_dask_id="TEST_DASK_ID",
    )
    _test_esp_dask.connect()
    return _test_esp_dask
