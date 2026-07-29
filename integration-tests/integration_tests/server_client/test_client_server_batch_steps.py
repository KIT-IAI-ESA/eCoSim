from integration_tests.server_client.pre_sets.pre_set_two_clients import PreSetTwoClientsData


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

    server_thread.join()
    pre_set_two_clients.server.print_measurement_statistics()

    pre_set_two_clients.verify_successful_run()


def test_client_server_batch_steps_with_empty_repository(pre_set_two_clients: PreSetTwoClientsData) -> None:
    server_thread = pre_set_two_clients.start_server_async()

    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()

    server_thread.join(15)
    pre_set_two_clients.server.print_measurement_statistics()

    pre_set_two_clients.verify_successful_run()


def test_client_server_batch_steps_different_completed_steps_step4_step5(pre_set_two_clients: PreSetTwoClientsData) -> None:
    for step in range(4):
        pre_set_two_clients.add_client_1_measurement(
            step=step,
            output_value=pre_set_two_clients.client_1_output_value_at_step(step),
            input_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )
    for step in range(5):
        pre_set_two_clients.add_client_2_measurement(
            step=step,
            output_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )

    server_thread = pre_set_two_clients.start_server_async()

    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()

    server_thread.join()
    pre_set_two_clients.server.print_measurement_statistics()

    pre_set_two_clients.verify_successful_run()


def test_client_server_batch_steps_different_completed_steps_step1_step5(pre_set_two_clients: PreSetTwoClientsData) -> None:
    for step in range(1):
        pre_set_two_clients.add_client_1_measurement(
            step=step,
            output_value=pre_set_two_clients.client_1_output_value_at_step(step),
            input_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )
    for step in range(5):
        pre_set_two_clients.add_client_2_measurement(
            step=step,
            output_value=pre_set_two_clients.client_2_output_value_at_step(step),
        )

    server_thread = pre_set_two_clients.start_server_async()

    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()

    server_thread.join()
    pre_set_two_clients.server.print_measurement_statistics()

    pre_set_two_clients.verify_successful_run()
