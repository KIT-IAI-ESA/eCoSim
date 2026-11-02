from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest
from ecosim_common.config.db_config_overwrite import DbConfigOverwrite
from ecosim_server.config.server_config import ServerConfig
from tests.data.generate_server_config import write_server_config_file
from tests.tech.db.postgres_test_cluster import PostgresTestCluster
from tests.tech.db.postgres_test_process import HOST

PASSWORD = "role_password"
WRONG_PASSWORD = "wrong_password"


@dataclass(frozen=True)
class PasswordSources:
    cluster: PostgresTestCluster
    directory: Path
    monkeypatch: pytest.MonkeyPatch

    def new_role(self, password: str = PASSWORD) -> str:
        name = f"test_{uuid4().hex}"
        self.cluster.create_role(name=name, password=password)
        return name

    def set_environment_variable(
        self,
        role: str,
        password: str,
    ) -> None:
        self.monkeypatch.setenv(name="PGPASSWORD", value=password)

    def set_password_file(
        self,
        role: str,
        password: str,
        database: str = "*",
        mode: int = 0o600,
    ) -> None:
        file = self._write_password_file(name="password_file", role=role, password=password, database=database, mode=mode)
        self.monkeypatch.setenv(name="PGPASSFILE", value=str(file))

    def set_home_directory(
        self,
        role: str,
        password: str,
    ) -> None:
        self._write_password_file(name=".pgpass", role=role, password=password)
        self.monkeypatch.delenv(name="PGPASSFILE")

    def _write_password_file(
        self,
        name: str,
        role: str,
        password: str,
        database: str = "*",
        mode: int = 0o600,
    ) -> Path:
        escaped_password = password.replace("\\", "\\\\").replace(":", "\\:")
        file = self.directory / name
        file.write_text(f"{HOST}:{self.cluster.port}:{database}:{role}:{escaped_password}\n", encoding="utf-8")
        file.chmod(mode)
        return file

    def server_config(
        self,
        role: str,
        password: str | None = None,
        command_line_password: str | None = None,
    ) -> ServerConfig:
        return ServerConfig.of_file(
            file=write_server_config_file(directory=self.directory, host=HOST, port=self.cluster.port, username=role, password=password),
            db_config_overwrite=DbConfigOverwrite(_name=role, _schema="postgres", _user_password=command_line_password),
        )


SetPassword = Callable[..., None]
ALL_SOURCES: list[SetPassword] = [
    PasswordSources.set_environment_variable,
    PasswordSources.set_password_file,
    PasswordSources.set_home_directory,
]
