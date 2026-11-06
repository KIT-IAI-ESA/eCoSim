from ecosim_server.tech.db.db_types import DTOMeta
from sqlalchemy.orm import declarative_base

SimControlDB_Base = declarative_base(metaclass=DTOMeta)
