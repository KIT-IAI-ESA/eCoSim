import os
import sys

from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.tech.db.db_types import DTOMeta
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base


def _resolve_schema() -> str:
    if "PYTEST_CURRENT_TEST" in os.environ or any("pytest" in arg for arg in sys.argv):
        return "postgres"
    try:
        return CLIArguments().db_config_overwrite().schema(default="ERROR_NO_SCHEMA")
    except (SystemExit, ValueError, TypeError):
        return "postgres"


SimControlDB_Base = declarative_base(
    metaclass=DTOMeta,
    metadata=MetaData(
        schema=_resolve_schema(),
    ),
)
