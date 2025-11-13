import datetime

from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from ecosim_common.communication.data.simulation_step_batch_request import (
    SimulationStepBatchRequest,
)
from ecosim_common.tech.datetime.date_time_to_millis import (
    date_time_to_millis_since_unix_epoch,
)

START_TIME_UTC: datetime.datetime = datetime.datetime(
    2025,
    3,
    21,
    14,
    11,
    22,
    333_000,
    tzinfo=datetime.timezone.utc,
)
ENTRY_TIME = datetime.datetime(
    2025,
    3,
    21,
    14,
    11,
    33,
    123_000,
    tzinfo=datetime.timezone.utc,
)

START_TIME_MILLIS_UTC = 1742566282333
ENTRY_TIME_MILLIS_UTC = 1742566293123


def test_to_json() -> None:
    request = SimulationStepBatchRequest(
        start_datetime=START_TIME_UTC,
        inputs={
            ENTRY_TIME: [
                ProtocolInterfaceValue(
                    name="Test_Interface",
                    value=333.444,
                ),
            ],
        },
    )
    json = request.to_json()
    assert json == {
        "inputs": {
            ENTRY_TIME_MILLIS_UTC: [{"name": "Test_Interface", "value": 333.444}],
        },
        "start_datetime": START_TIME_MILLIS_UTC,
    }


def test_of_json() -> None:
    json = {
        "inputs": {
            ENTRY_TIME_MILLIS_UTC: [{"name": "Test_Interface", "value": 333.444}],
        },
        "start_datetime": START_TIME_MILLIS_UTC,
    }
    request = SimulationStepBatchRequest.of_json(json)
    assert request.start_datetime == START_TIME_UTC
    assert len(request.inputs.values()) == 1
    assert len(request.inputs[ENTRY_TIME]) == 1
    assert request.inputs[ENTRY_TIME][0].name == "Test_Interface"
    assert request.inputs[ENTRY_TIME][0].value == 333.444


def test_of_json_with_non_utc_key() -> None:
    date_time_local = datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
    )
    json = {
        "inputs": {
            date_time_to_millis_since_unix_epoch(date_time_local): [
                {"name": "Test_Interface", "value": 333.444},
            ],
        },
        "start_datetime": START_TIME_MILLIS_UTC,
    }
    request = SimulationStepBatchRequest.of_json(json)
    assert request.start_datetime == START_TIME_UTC
    assert len(request.inputs.values()) == 1
    assert len(request.inputs[date_time_local]) == 1
    assert request.inputs[date_time_local][0].name == "Test_Interface"
    assert request.inputs[date_time_local][0].value == 333.444
