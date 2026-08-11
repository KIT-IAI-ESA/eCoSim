from __future__ import annotations

from typing import Any

from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.tech.db.db_types import DTO, GenericEntity, GenericId
from sqlalchemy import Engine, Executable, create_engine, func, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


# TODO_OSR: refactor to dataclass
class DBConnection:
    _logger = ESPLogger("DBConnection")

    def __init__(
        self,
        db_config: DatabaseConfig,
        base_model: Any,
    ) -> None:
        self._db_url: str = db_config.generate_sqlalchemy_db_url()
        self._base_model = base_model
        self._db_engine: Engine = create_engine(self._db_url)
        self.default_schema: str = db_config.schema
        self._db_engine = self._db_engine.execution_options(schema_translate_map={"": self.default_schema})
        self._base_model.metadata.create_all(self._db_engine)

    def create_measurement_table(
        self,
        table: type[GenericEntity],
    ) -> None:
        table_name = table.__tablename__  # type: ignore # __tablename__ is part of SQLAlchemy
        if self.table_exists(table_name):
            DBConnection._logger.debug("Table %s already exists -> skipping creation", table_name)
            return
        DBConnection._logger.debug("Creating table %s", table_name)
        table.__table__.create(self._db_engine)  # type: ignore # __table__ is part of SQLAlchemy

    def table_exists(
        self,
        table_name: str,
    ) -> bool:
        try:
            inspector = inspect(self._db_engine)
            return inspector.has_table(table_name)
        except OperationalError as e:
            DBConnection._logger.error("An error occurred while checking if table exists: %s", e)
            return False

    def insert_into(
        self,
        param: DTO[GenericId],
    ) -> GenericId:
        with Session(self._db_engine) as session:
            session.add(param)
            session.commit()
            return param.id()

    def upsert(
        self,
        param: DTO[GenericId],
    ) -> GenericId:
        with Session(self._db_engine) as session:
            session.merge(param)
            session.commit()
            return param.id()

    def select_by_id(
        self,
        table: type[GenericEntity],
        entity_id: GenericId,
    ) -> DTO[GenericId] | None:
        with Session(self._db_engine) as session:
            return session.query(table).filter_by(**{table.id_column().name: entity_id}).first()

    def update(
        self,
        param: DTO[GenericId],
    ) -> None:
        table = param.__class__
        with Session(self._db_engine) as session:
            current = session.query(table).filter_by(**{table.id_column().name: param.id()}).first()
            for key, value in param.__dict__.items():
                if key != table.id_column().name and not key.startswith("_sa_"):
                    setattr(current, key, value)
            session.commit()

    def count_entries(
        self,
        table: type[DTO[GenericId]],
    ) -> int:
        # pass a column like SimulationStateDTO.variation_id
        with Session(self._db_engine) as session:
            return session.query(func.count(table.id_column())).scalar()

    def clear_table(
        self,
        table: type[DTO[GenericId]],
    ) -> None:
        with Session(self._db_engine) as session:
            session.query(table).delete()
            session.commit()

    def execute(
        self,
        statement: Executable,
    ) -> None:
        with Session(self._db_engine) as session:
            session.execute(statement)
            session.commit()

    def session(self) -> Session:
        return Session(self._db_engine)
