from pathlib import Path

from ecosim_common.config.database_type import DatabaseType
from tests.data.generate_server_config import generate_server_config


def test_file_results_show_only_their_directory(tmp_path: Path) -> None:
    database = generate_server_config(database_type=DatabaseType.FILE, database_directory=tmp_path).database

    assert database.start_up_values() == {"Results directory": str(tmp_path)}


def test_postgres_results_show_the_database_server_its_name_and_the_schema() -> None:
    database = generate_server_config(database_type=DatabaseType.POSTGRES, database_schema="temp_schema").database

    assert database.start_up_values() == {"Database server": "localhost:5432", "Database name": "sim_control", "Database schema": "temp_schema"}


def test_postgres_results_without_a_server_name_are_on_this_computer() -> None:
    database = generate_server_config(database_type=DatabaseType.POSTGRES, database_host="").database

    assert (database.start_up_values()["Database server"], database.results_location()) == (
        "port 5432 of this computer",
        "PostgreSQL database sim_control on port 5432 of this computer, schema sim_control",
    )


def test_the_image_renderer_shows_up_only_when_it_is_configured() -> None:
    without_renderer = generate_server_config().server
    with_renderer = generate_server_config(image_renderer_port=8765, image_renderer_interval=10).server

    assert without_renderer.image_renderer_start_up_values() == {}
    assert with_renderer.image_renderer_start_up_values() == {"Image renderer socket": "localhost:8765", "Image renderer interval": "10"}
