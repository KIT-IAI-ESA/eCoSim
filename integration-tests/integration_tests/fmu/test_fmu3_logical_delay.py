from pathlib import Path

from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import config_parser_for_resource, fmu3_model_path
from integration_tests.fmu.fmu3_state_space_model import state_space_outputs
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.server_client.logical_delay_setup import HOST, delayed_simulation_config, sender_client, server_on_free_port


@skip_unless_fmpy_loads(fmu3_model_path())
def test_array_input_of_an_fmu_receives_a_list_start_value_and_delayed_lists(communication_protocol: CommunicationProtocol, tmp_path: Path) -> None:
    # the fmu input is factor * second in every step, as state_space_outputs expects
    factors = (1.0, 2.0, 3.0)
    simulation_config = delayed_simulation_config(
        directory=tmp_path,
        steps=4,
        delay=1,
        start_value=list(factors),
        receiver_name="fmu3",
        receiver_model="state_space",
        delayed_input="u",
        receiver_outputs=("y",),
    )
    server = server_on_free_port(communication_protocol=communication_protocol, simulation_config=simulation_config)
    sender = sender_client(server=server, sent_value_after_seconds=lambda seconds: [factor * (seconds + 1) for factor in factors])
    fmu3_client = FMU3Client.of(
        config_parser=config_parser_for_resource("integration/models/fmu3/configs/state_space.ini"),
        config_override=ClientConfigOverride(server_host=HOST, server_port=server.port(), communication_protocol=communication_protocol),
    )

    server.start_in_thread()
    server.wait_until_listening()
    fmu3_client.start()
    sender.start()
    server.assert_finishing_in_time()

    measurement_repository = server.measurement_repository(client_id=fmu3_client.client_id)
    if not isinstance(measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")
    assert measurement_repository.values_by_step(interface="y") == [state_space_outputs(second=second, factors=factors) for second in range(1, 5)]
