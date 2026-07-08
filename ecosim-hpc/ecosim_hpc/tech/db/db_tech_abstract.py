from abc import ABC, abstractmethod

from ecosim_hpc.tech.db.db_connection import DBConnection


class DbTechAbstract(ABC):

    @abstractmethod
    def init_db(self) -> None:
        pass

    @abstractmethod
    def db_connection(self) -> DBConnection:
        pass
