import pytest
from ecosim_common.config.database_type import DatabaseType


def test_postgres_is_parsed() -> None:
    assert DatabaseType.of("postgres") is DatabaseType.POSTGRES


def test_file_is_parsed() -> None:
    assert DatabaseType.of("file") is DatabaseType.FILE


def test_the_value_is_case_insensitive() -> None:
    assert DatabaseType.of("FILE") is DatabaseType.FILE


def test_surrounding_whitespace_is_ignored() -> None:
    assert DatabaseType.of(" file ") is DatabaseType.FILE


def test_an_unknown_type_fails() -> None:
    with pytest.raises(ValueError):
        DatabaseType.of("mysql")


def test_the_type_is_serialized_as_its_config_value() -> None:
    assert DatabaseType.FILE.serialized == "file"
    assert DatabaseType.POSTGRES.value == "postgres"
