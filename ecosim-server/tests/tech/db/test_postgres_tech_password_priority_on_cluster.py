import pytest
from ecosim_server.tech.db.postgres_tech import PostgresTech
from sqlalchemy.exc import OperationalError
from tests.tech.db.password_sources import ALL_SOURCES, PASSWORD, WRONG_PASSWORD, PasswordSources, SetPassword
from tests.tech.db.postgres_test_cluster import PostgresTestCluster


@pytest.mark.parametrize("set_source", ALL_SOURCES)
def test_a_configured_password_goes_before_a_wrong_one_from_outside_the_config(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
    set_source: SetPassword,
) -> None:
    role = password_sources.new_role()
    set_source(password_sources, role=role, password=WRONG_PASSWORD)

    PostgresTech(password_sources.server_config(role=role, password=PASSWORD)).init_db()

    assert plain_cluster.schema_exists(database=role, schema="postgres")


@pytest.mark.parametrize("set_source", ALL_SOURCES)
def test_a_wrong_configured_password_does_not_fall_back_to_a_right_one_from_outside_the_config(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
    set_source: SetPassword,
) -> None:
    role = password_sources.new_role()
    set_source(password_sources, role=role, password=PASSWORD)

    with pytest.raises(OperationalError, match="password authentication failed"):
        PostgresTech(password_sources.server_config(role=role, password=WRONG_PASSWORD)).init_db()

    assert plain_cluster.database_id(role) is None


def test_a_password_on_the_command_line_goes_before_the_config_file_and_the_environment(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
) -> None:
    role = password_sources.new_role()
    password_sources.set_environment_variable(role=role, password=WRONG_PASSWORD)
    config = password_sources.server_config(role=role, password=WRONG_PASSWORD, command_line_password=PASSWORD)

    PostgresTech(config).init_db()

    assert plain_cluster.schema_exists(database=role, schema="postgres")


def test_the_environment_variable_goes_before_the_password_file(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
) -> None:
    role = password_sources.new_role()
    password_sources.set_environment_variable(role=role, password=PASSWORD)
    password_sources.set_password_file(role=role, password=WRONG_PASSWORD)

    PostgresTech(password_sources.server_config(role=role)).init_db()

    assert plain_cluster.schema_exists(database=role, schema="postgres")
