import pytest
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.simulation.model_interface_id import ModelInterfaceId


@pytest.mark.parametrize("required", [True, False])
def test_required_accepts_a_json_boolean(required: bool) -> None:
    interface = ModelInterfaceClient.of_json_client_config(
        model_interface_id=ModelInterfaceId(model_name="house", interface="T_out"),
        interface={"name": "T_out", "required": required},
        interface_type=InterfaceType.INPUT,
    )

    assert interface.required is required
