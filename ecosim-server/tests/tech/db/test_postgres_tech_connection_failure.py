import pytest
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.tech.db.postgres_tech import PostgresTech
from sqlalchemy.exc import OperationalError
from tests.data.generate_server_config import generate_server_config
from tests.tech.db.postgres_test_process import HOST, free_port
from tests.tech.db.special_passwords import PASSWORD_PARTS, PASSWORD_WITH_PARTS


def test_a_failed_connection_does_not_show_any_part_of_the_password() -> None:
    config = generate_server_config(
        database_host=HOST,
        database_port=free_port(),
        database_password=PASSWORD_WITH_PARTS,
        database_ssl=False,
    )

    with pytest.raises(OperationalError, match=HOST) as error:
        PostgresTech(config).init_db()

    for part in PASSWORD_PARTS:
        assert part not in str(error.value)


def test_a_refused_connection_does_not_fall_through_to_the_maintenance_database(monkeypatch: pytest.MonkeyPatch) -> None:
    generated: list[DatabaseConfig] = []
    monkeypatch.setattr(DatabaseConfig, "generate_sqlalchemy_root_url", lambda config: generated.append(config))
    config = generate_server_config(database_host=HOST, database_port=free_port(), database_ssl=False)

    with pytest.raises(OperationalError, match=HOST):
        PostgresTech(config).init_db()

    assert not generated
