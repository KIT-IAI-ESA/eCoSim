from integration_tests.server_client.performance.tooling.performance_result_setup import current_test_name


def test_the_test_name_is_the_pytest_function_without_parameters() -> None:
    assert current_test_name() == "test_the_test_name_is_the_pytest_function_without_parameters"
