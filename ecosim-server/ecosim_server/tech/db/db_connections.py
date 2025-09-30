from __future__ import annotations

from typing import Any

from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_tech_abstract import DbTechAbstract
from ecosim_server.tech.db.postgres_tech import PostgresTech
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.singleton import Singleton
from ecosim_server.config.server_config import ServerConfig


class DBConnections(metaclass=Singleton):
    _logger = ESPLogger("DBConnection")

    @staticmethod
    def instance() -> DBConnections:
        # this is not nice, but it works since the actual initialization is happening before the first instance() call
        return DBConnections(None)  # type: ignore

    # noinspection PyUnusedLocal
    def __init__(self,
                 server_config: ServerConfig,
                 *args: Any,
                 **kwargs: Any,
                 ) -> None:
        # Prevent __init__ from running more than once in the singleton pattern
        if hasattr(self, '_initialized'):
            DBConnections._logger.warning("Init method called multiple times.")
            return

        db_tech = self._get_db_tech(server_config)
        db_tech.init_db()

        self._initialized = True
        self.main: DBConnection = db_tech.db_connection()

    def _get_db_tech(self,
                     server_config: ServerConfig,
                     ) -> DbTechAbstract:
        match server_config.database.type:
            case "postgres":
                return PostgresTech(server_config)
            case _:
                raise Exception(f"Unsupported database type '{server_config.database.type}'")
