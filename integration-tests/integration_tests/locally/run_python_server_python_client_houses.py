from integration_tests.locally.base_run_it import run_integration_test

run_integration_test(
    start_script="/integration_test/fmus/houses/run_python_server_python_client_test.sh 200 480s",
    copy_logs=True,
    copy_results=True,
    copy_destination_path="/tmp",
)
