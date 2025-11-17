from datetime import datetime
from typing import Tuple

from ecosim_common.communication.data.protocol_interface_value import (
    InterfaceValueType,
    ProtocolInterfaceValue,
)
from integration_tests.server_client.pre_sets.pre_set_two_clients import PreSetTwoClientsData
from integration_tests.tech.db.measurement_repository_in_memory import (
    MeasurementRepositoryInMemory,
)


def test_client_server_batch_steps(pre_set_two_clients: PreSetTwoClientsData) -> None:
    for step in range(5):
        pre_set_two_clients.add_client_1_measurement(
            step=step,
            output_value=pre_set_two_clients.client_1_output_value_at_step(step),
            input_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )
        pre_set_two_clients.add_client_2_measurement(
            step=step,
            output_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )

    server_thread = pre_set_two_clients.start_server_async()

    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()

    server_thread.join(timeout=7)

    client_1_measurement_repository = pre_set_two_clients.measurement_repository_client_1()

    if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    client_1_measurement_repository.assert_entry_count(pre_set_two_clients.steps)

    def assert_for_each_record(
        timestamp: datetime,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> bool:
        current_step = pre_set_two_clients.date_to_step(timestamp)

        output_value: InterfaceValueType | None = None
        input_value: InterfaceValueType | None = None
        for value in values:
            if value.name == "Interface_Output_1":
                output_value = value.value
            elif value.name == "Interface_Input_1":
                input_value = value.value
        assert output_value is not None, (
            f"Missing output interface value for step {current_step}"
        )
        assert input_value is not None, (
            f"Missing input interface value for step {current_step}"
        )

        expected_output = pre_set_two_clients.client_1_output_value_at_step(int(current_step))
        expected_input = pre_set_two_clients.client_2_output_value_at_step(int(current_step))
        assert input_value == expected_input, (
            f"failed at step {current_step} with input value {input_value} != {expected_input}"
        )
        assert output_value == expected_output, (
            f"failed at step {current_step} with output value {output_value} != {expected_output}"
        )
        return values[0].value == expected_output

    client_1_measurement_repository.assert_for_each_record(assert_for_each_record)
