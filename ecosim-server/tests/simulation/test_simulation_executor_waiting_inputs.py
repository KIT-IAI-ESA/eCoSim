from pathlib import Path

from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_input, create_output, create_simulator
from tests.simulation.simulation_executor_test_setup import error_of_bounded_run, executor_for_simulation_config


def test_a_step_that_cannot_go_on_names_the_inputs_still_waiting(tmp_path: Path) -> None:
    file = config_file(
        tmp_path,
        create_simulator("sender", create_output("sent")),
        create_simulator("receiver", create_input("received", simulator="0", interface="sent")),
    )
    simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)
    # the default answer of a fake client has no outputs, so "received" never gets a value
    executor, _ = executor_for_simulation_config(
        simulation_config=simulation_config,
        reactions_by_client={client_id: {} for client_id in simulation_config.client_ids()},
    )

    error = error_of_bounded_run(executor)

    waiting_input = SimulatorInterfaceId(simulator_name="receiver", model_interface_id=ModelInterfaceId(model_name="receiver", interface="received"))
    assert isinstance(error, RuntimeError), error
    assert str(waiting_input) in str(error)
