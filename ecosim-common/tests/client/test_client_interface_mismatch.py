import pytest
from ecosim_common.client.config.client_config import SimulatorConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.communication.message_type import MessageType

from tests.client.spy_simulator_client import SpySimulatorClient


def test_the_client_warns_about_every_input_of_the_simulation_config_that_its_fmc_file_lacks(caplog: pytest.LogCaptureFixture) -> None:
    # the test .fmc has the inputs input_1, input_2 (required) and input_3
    SpySimulatorClient.of_ended_run(
        message_types=[MessageType.INTERFACE_SETTINGS],
        payloads={MessageType.INTERFACE_SETTINGS: ServerInterfaceSettings(inputs=["input_2", "input_33", "rain"], outputs=[])},
        simulator_config=SimulatorConfig(simulator_name="house", model_name="house", fmc_file="fmc_interface_test.fmc", type=ClientType.FMU_2),
    )

    assert [record.getMessage() for record in caplog.records if record.name == "Client" and record.levelname == "WARNING"] == [
        "The simulation config connects input input_33, but fmc_interface_test.fmc has no input of that name. Did you mean input_3?",
        "The simulation config connects input rain, but fmc_interface_test.fmc has no input of that name.",
    ]
