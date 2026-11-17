from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ecosim_common.config.database_type import DatabaseType


@dataclass(frozen=True)
class DbConfigOverwrite:
    _host: str | None = None
    _port: int | None = None
    _user: str | None = None
    _user_password: str | None = field(default=None, repr=False)
    _name: str | None = None
    _schema: str | None = None
    _ssl: bool | None = None
    _drop_existing_schema: bool | None = None
    _type: DatabaseType | None = None
    _directory: Path | None = None

    def host(
        self,
        default: str,
    ) -> str:
        return self._host or default

    def port(
        self,
        read_default: Callable[[], int],
    ) -> int:
        return self._port or read_default()

    def user(
        self,
        default: str,
    ) -> str:
        return self._user or default

    def user_password(
        self,
        default: str,
    ) -> str:
        return self._user_password or default

    def name(
        self,
        default: str,
    ) -> str:
        return self._name or default

    def schema(
        self,
        default: str,
    ) -> str:
        return self._schema or default

    def ssl(
        self,
        default: bool,
    ) -> bool:
        return default if self._ssl is None else self._ssl

    def drop_existing_schema(
        self,
        default: bool,
    ) -> bool:
        return self._drop_existing_schema or default

    def type(
        self,
        default: DatabaseType,
    ) -> DatabaseType:
        return self._type or default

    def directory(
        self,
        default: Path,
    ) -> Path:
        return self._directory or default
