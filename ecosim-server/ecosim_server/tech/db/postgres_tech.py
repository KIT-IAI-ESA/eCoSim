import re

from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_tech_abstract import DbTechAbstract
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from psycopg import sql
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import OperationalError


class PostgresTech(DbTechAbstract):
    _logger = ESPLogger("PostgresTech")

    def __init__(
        self,
        server_config: ServerConfig,
    ):
        self.server_config = server_config

    def db_connection(self) -> DBConnection:
        PostgresTech._logger.debug("Creating DB connection to %s", self.server_config.database.name)
        return DBConnection.of_db_config_and_model(
            db_config=self.server_config.database,
            base_model=SimControlDB_Base,
        )

    def init_db(self) -> None:
        engine = create_engine(self.server_config.database.generate_sqlalchemy_db_url())
        try:
            self._create_database_if_missing(engine)
            self._create_schema(engine)
        finally:
            engine.dispose()

    def _create_database_if_missing(self, engine: Engine) -> None:
        try:
            with engine.connect():
                PostgresTech._logger.debug("Database '%s' already exists - no need for creation.", self.server_config.database.name)
        except OperationalError as error:
            if not self._mentions_database(error):
                raise
            self._create_database_unless_it_exists(error)

    def _mentions_database(self, error: OperationalError) -> bool:
        # a failed connection has no SQLSTATE and its message is translated, only the name is reliable
        name = re.escape(self.server_config.database.name)
        return re.search(rf"(?<![\w.-]){name}(?![\w.-])", str(error.orig)) is not None

    def _create_database_unless_it_exists(self, connection_error: OperationalError) -> None:
        root_engine = create_engine(self.server_config.database.generate_sqlalchemy_root_url(), isolation_level="AUTOCOMMIT")
        try:
            with self._connect_to_maintenance_database(root_engine=root_engine, connection_error=connection_error) as connection:
                if self._database_exists(connection):
                    raise connection_error
                self._create_database(connection)
        finally:
            root_engine.dispose()

    @staticmethod
    def _connect_to_maintenance_database(
        root_engine: Engine,
        connection_error: OperationalError,
    ) -> Connection:
        try:
            return root_engine.connect()
        except OperationalError as error:
            raise connection_error from error

    def _database_exists(self, connection: Connection) -> bool:
        statement = text("SELECT 1 FROM pg_database WHERE datname = :name")
        return connection.execute(statement=statement, parameters={"name": self.server_config.database.name}).scalar() is not None

    def _create_database(self, connection: Connection) -> None:
        name = self.server_config.database.name
        statement = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)).as_string()
        connection.exec_driver_sql(statement, execution_options={"no_parameters": True})
        PostgresTech._logger.debug("Database '%s' created successfully.", name)

    def _create_schema(self, engine: Engine) -> None:
        schema = self.server_config.database.schema
        with engine.connect() as connection:
            self._drop_existing_schema(connection=connection, schema=schema)
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.commit()
            PostgresTech._logger.debug("Schema '%s' created", schema)

    def _drop_existing_schema(
        self,
        connection: Connection,
        schema: str,
    ) -> None:
        result = connection.execute(text(f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema}'"))
        if not result.scalar():
            return
        if not self.server_config.database.drop_existing_schema:
            raise RuntimeError(
                f"Schema '{schema}' already exists. This means there was already an execution for this run. "
                + "This is most likely an error in your local setup and should not occur on live.",
            )
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
