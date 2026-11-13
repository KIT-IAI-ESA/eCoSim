import time

from dask import distributed as dd


def wait_until_server_connection_listener_started(
    dask_client: dd.Client,
    timeout_in_seconds: float = 10.0,
) -> None:
    deadline = time.monotonic() + timeout_in_seconds
    listener_task_name = "_listen_on_connection_internal"
    while not any(key.startswith(listener_task_name) for keys in dask_client.processing().values() for key in keys):
        if time.monotonic() > deadline:
            raise TimeoutError(f"The server's connection listener did not start. Did the task name change (current={listener_task_name})?")
        time.sleep(0.1)
