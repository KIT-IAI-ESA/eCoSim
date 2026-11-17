from pathlib import Path

from ecosim_common.config.database_type import DatabaseType
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.data.repositories import create_repositories
from ecosim_server.server import Server
from ecosim_test_common.test_data.error_recording_thread import ErrorRecordingThread
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from tests.data.generate_postgres_name_config import generate_client_simulator_config, generate_simulation_config
from tests.data.generate_server_config import generate_server_config


def test_a_server_thread_that_fails_after_a_shutdown_counts_as_stopped_by_a_signal(tmp_path: Path) -> None:
    server_config = generate_server_config(port=get_free_port(), database_type=DatabaseType.FILE, database_directory=tmp_path)
    simulation_config = generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")])
    server = Server(
        _simulation_config=simulation_config,
        _server_config=server_config,
        _repositories=create_repositories(server_config=server_config, simulation_config=simulation_config),
    )
    server_run = ErrorRecordingThread(target=server.start)
    server_run.start()
    assert server._channel.is_listening_on_connection_event().wait(timeout=WAIT_TIMEOUT_IN_SECONDS)  # noqa: SLF001

    ShutdownManager().set_shutdown_at_application_end()

    server_run.assert_ends_within(timeout_in_seconds=WAIT_TIMEOUT_IN_SECONDS)
    assert server.run_summary().failure_reason == "stopped by Ctrl-C or a kill signal"
