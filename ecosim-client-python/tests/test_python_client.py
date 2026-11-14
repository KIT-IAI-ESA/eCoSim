from typing import Any

from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config
from ecosim_test_common.test_data.python_models import ClockModel, DoublingModel, EchoModel, ScriptedOutputsModel

from ecosim_client_python.python_client import PythonClient
from ecosim_client_python.python_model import PythonModel


def _client_of(model: Any, server_used_outputs: list[str]) -> PythonClient:
    execution_config = ExecutionConfig()
    execution_config.set_server_interface_settings(server_interface_settings=ServerInterfaceSettings(inputs=[], outputs=server_used_outputs))
    return PythonClient(
        _client_config=generate_mocked_client_config(),
        _execution_config=execution_config,
        _model=PythonModel.of_object(model=model, model_reference="room:Room"),
    )


def test_do_step_gets_the_time_at_the_start_of_each_step() -> None:
    client = _client_of(model=ClockModel(), server_used_outputs=["time", "step_size"])
    client.on_simulation_start()

    client.on_simulation_step(received_inputs={}, step_size_in_seconds=900.0)
    second_step = client.on_simulation_step(received_inputs={}, step_size_in_seconds=900.0)

    assert second_step.interface_values == [ProtocolInterfaceValue(name="time", value=900.0), ProtocolInterfaceValue(name="step_size", value=900.0)]


def test_the_inputs_of_the_step_reach_the_model() -> None:
    client = _client_of(model=DoublingModel(), server_used_outputs=["y"])
    client.on_simulation_start()

    step = client.on_simulation_step(received_inputs={"u": 1.5}, step_size_in_seconds=1.0)

    assert step.interface_values == [ProtocolInterfaceValue(name="y", value=3.0)]


def test_a_list_input_reaches_the_model() -> None:
    client = _client_of(model=EchoModel(), server_used_outputs=["y"])
    client.on_simulation_start()

    step = client.on_simulation_step(received_inputs={"u": [1.0, 2.0]}, step_size_in_seconds=1.0)

    assert step.interface_values == [ProtocolInterfaceValue(name="y", value=[1.0, 2.0])]


def test_a_model_that_never_started_is_not_cleared() -> None:
    model = ScriptedOutputsModel()
    client = _client_of(model=model, server_used_outputs=[])

    client.on_app_shutdown()

    assert model.clear_calls == 0


def test_a_started_model_is_cleared_at_the_shutdown() -> None:
    model = ScriptedOutputsModel(start_outputs={})
    client = _client_of(model=model, server_used_outputs=[])
    client.on_simulation_start()

    client.on_app_shutdown()

    assert model.clear_calls == 1
