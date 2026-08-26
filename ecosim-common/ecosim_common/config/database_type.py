from enum import Enum
from typing import assert_never


class DatabaseType(str, Enum):
    """Where the server stores the simulation results."""

    POSTGRES = "postgres"
    FILE = "file"

    @staticmethod
    def of(database_type: str) -> "DatabaseType":
        for member in DatabaseType:
            if member.value == database_type.strip().lower():
                return member
        raise ValueError(f"Type {database_type} not known. Possible: {[member.value for member in DatabaseType]}")

    @property
    def serialized(self) -> str:
        match self:
            case DatabaseType.POSTGRES:
                return "postgres"
            case DatabaseType.FILE:
                return "file"
            case _:
                assert_never(self)
