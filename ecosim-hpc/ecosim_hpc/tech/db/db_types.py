from abc import abstractmethod, ABC, ABCMeta
from typing import Any, TypeVar, Generic

from sqlalchemy.orm import DeclarativeMeta

GenericId = TypeVar('GenericId')
GenericEntity = TypeVar('GenericEntity', bound='DTO')


class DTO(ABC, Generic[GenericId]):
    @abstractmethod
    def id(self) -> GenericId:
        pass

    @staticmethod
    @abstractmethod
    def id_column() -> Any:
        pass


class DTOMeta(DeclarativeMeta, ABCMeta):
    pass
