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


def test_to_json() -> None:
    date_time = datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone.utc,
    )
    request = SimulationStepBatchRequest(
        step_size_ms=2222,
        inputs={
            date_time: [
                ProtocolInterfaceValue(
                    name="Test_Interface",
                    value=333.444,
                ),
            ],
        },
    )
    json = request.to_json()
    assert json == {
        "inputs": {1742566293123: [{"name": "Test_Interface", "value": 333.444}]},
        "step_size_ms": 2222,
    }


def test_of_json() -> None:
    date_time = datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone.utc,
    )
    json = {
        "inputs": {1742566293123: [{"name": "Test_Interface", "value": 333.444}]},
        "step_size_ms": 2222,
    }
    request = SimulationStepBatchRequest.of_json(json)
    assert request.step_size_ms == 2222
    assert len(request.inputs.values()) == 1
    assert len(request.inputs[date_time]) == 1
    assert request.inputs[date_time][0].name == "Test_Interface"
    assert request.inputs[date_time][0].value == 333.444


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
    date_time_utc = datetime.datetime(
        2025,
        3,
        21,
        13,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone.utc,
    )
    json = {
        "inputs": {
            date_time_to_millis_since_unix_epoch(date_time_utc): [
                {"name": "Test_Interface", "value": 333.444},
            ],
        },
        "step_size_ms": 2222,
    }
    request = SimulationStepBatchRequest.of_json(json)
    assert request.step_size_ms == 2222
    assert len(request.inputs.values()) == 1
    assert len(request.inputs[date_time_local]) == 1
    assert request.inputs[date_time_local][0].name == "Test_Interface"
    assert request.inputs[date_time_local][0].value == 333.444
