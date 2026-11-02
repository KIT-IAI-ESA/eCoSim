import pytest
from ecosim_server.tech.db.postgres_tech import PostgresTech
from sqlalchemy.exc import OperationalError
from tests.tech.db.password_sources import ALL_SOURCES, PASSWORD, PasswordSources, SetPassword
from tests.tech.db.postgres_test_cluster import PostgresTestCluster, skip_in_ci
from tests.tech.db.special_passwords import PASSWORD_PARTS, PASSWORD_WITH_PARTS, SPECIAL_PASSWORDS

pytestmark = skip_in_ci

MAINTENANCE_DATABASE = "postgres"


@pytest.mark.parametrize("password", SPECIAL_PASSWORDS)
@pytest.mark.parametrize("set_source", ALL_SOURCES)
def test_a_password_from_outside_the_config_reaches_both_databases(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
    set_source: SetPassword,
    password: str,
) -> None:
    role = password_sources.new_role(password=password)
    set_source(password_sources, role=role, password=password)
    config = password_sources.server_config(role=role)

    PostgresTech(config).init_db()
    PostgresTech(config).db_connection()

    assert plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)
    assert plain_cluster.was_reached(database=role, username=role)
    assert plain_cluster.schema_exists(database=role, schema="postgres")


@pytest.mark.parametrize("set_source", ALL_SOURCES)
def test_an_empty_password_key_counts_as_no_password(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
    set_source: SetPassword,
) -> None:
    role = password_sources.new_role()
    set_source(password_sources, role=role, password=PASSWORD)

    PostgresTech(password_sources.server_config(role=role, password="")).init_db()

    assert plain_cluster.schema_exists(database=role, schema="postgres")


def test_an_existing_database_only_needs_a_password_file_entry_for_itself(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
) -> None:
    role = password_sources.new_role()
    plain_cluster.create_database(name=role, owner=role)
    password_sources.set_password_file(role=role, password=PASSWORD, database=role)

    PostgresTech(password_sources.server_config(role=role)).init_db()

    assert plain_cluster.schema_exists(database=role, schema="postgres")
    assert not plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)


def test_a_missing_database_needs_a_password_file_entry_for_the_maintenance_database(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
) -> None:
    role = password_sources.new_role()
    password_sources.set_password_file(role=role, password=PASSWORD, database=role)

    with pytest.raises(OperationalError, match="does not exist") as error:
        PostgresTech(password_sources.server_config(role=role)).init_db()

    assert "no password supplied" in str(error.value.__cause__)
    assert plain_cluster.database_id(role) is None


def test_no_password_anywhere_names_the_problem(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
) -> None:
    role = password_sources.new_role()

    with pytest.raises(OperationalError, match="no password supplied"):
        PostgresTech(password_sources.server_config(role=role)).init_db()


def test_a_password_file_others_can_read_is_ignored(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
) -> None:
    role = password_sources.new_role()
    password_sources.set_password_file(role=role, password=PASSWORD, mode=0o644)

    with pytest.raises(OperationalError, match="no password supplied"):
        PostgresTech(password_sources.server_config(role=role)).init_db()


@pytest.mark.parametrize("set_source", ALL_SOURCES)
def test_a_wrong_password_from_outside_the_config_does_not_show_any_part_of_it(
    plain_cluster: PostgresTestCluster,
    password_sources: PasswordSources,
    set_source: SetPassword,
) -> None:
    role = password_sources.new_role()
    set_source(password_sources, role=role, password=PASSWORD_WITH_PARTS)

    with pytest.raises(OperationalError, match="password authentication failed") as error:
        PostgresTech(password_sources.server_config(role=role)).init_db()

    for part in PASSWORD_PARTS:
        assert part not in str(error.value)
