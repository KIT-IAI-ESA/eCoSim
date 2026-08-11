from sqlalchemy import Engine, text, create_engine

from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_tech_abstract import DbTechAbstract
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.server_config import ServerConfig


class PostgresTech(DbTechAbstract):
    _logger = ESPLogger("PostgresTech")

    def __init__(
        self,
        server_config: ServerConfig,
    ):
        self.server_config = server_config

    def db_connection(self) -> DBConnection:
        PostgresTech._logger.debug("Creating DB connection to %s", self.server_config.database.name)
        return DBConnection(
            db_config=self.server_config.database,
            base_model=SimControlDB_Base,
        )

    def init_db(self) -> None:
        root_engine = create_engine(self.server_config.database.generate_sqlalchemy_root_url())
        self._prepare_database(root_engine)

    def _prepare_database(
        self,
        root_engine: Engine,
    ) -> None:
        db_name = self.server_config.database.name
        schema = self.server_config.database.schema
        with root_engine.connect() as root_connection:
            root_connection.execution_options(isolation_level="AUTOCOMMIT")
            result = root_connection.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"))
            exists = result.scalar() is not None
            if not exists:
                root_connection.execute(text(f"CREATE DATABASE {db_name}"))
                PostgresTech._logger.debug("Database '%s' created successfully.", db_name)
            else:
                PostgresTech._logger.debug("Database '%s' already exists - no need for creation.", db_name)

        existing_db = create_engine(self.server_config.database.generate_sqlalchemy_db_url())
        with existing_db.connect() as connection:
            result = connection.execute(
                text(f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema}'"),
            )
            if result.scalar():
                if not self.server_config.database.drop_existing_schema:
                    raise RuntimeError(
                        f"Schema '{schema}' already exists. This means there was already an execution for this run. "
                        + "This is most likely an error in your local setup and should not occur on live.",
                    )
                else:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.commit()
            PostgresTech._logger.debug("Schema '%s' created", schema)
