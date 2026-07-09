import os
import sys

from ecosim_hpc.tech.db.db_types import DTOMeta
from ecosim_server.config.cli_arguments import CLIArguments, CLIArgumentsHPC
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base


def _resolve_server_schema() -> str:
    if "PYTEST_CURRENT_TEST" in os.environ or any("pytest" in arg for arg in sys.argv):
        return "postgres"
    try:
        return CLIArguments().db_config_overwrite().schema(default="ERROR_NO_SCHEMA")
    except (SystemExit, ValueError, TypeError):
        return "postgres"


def _resolve_hpc_schema() -> str:
    if "PYTEST_CURRENT_TEST" in os.environ or any("pytest" in arg for arg in sys.argv):
        return "postgres"
    try:
        return CLIArgumentsHPC().db_config_overwrite().schema(default="ERROR_NO_SCHEMA")
    except (SystemExit, ValueError, TypeError):
        return "postgres"


if "ecosim_hpc.client_manager" in sys.modules:
    SimControlDB_Base = declarative_base(
        metaclass=DTOMeta,
        metadata=MetaData(
            schema=_resolve_hpc_schema(),
        ),
    )

elif "pytest" not in sys.modules:
    SimControlDB_Base = declarative_base(
        metaclass=DTOMeta,
        metadata=MetaData(
            schema=_resolve_server_schema(),
        ),
    )

else:
    SimControlDB_Base = declarative_base(
        metaclass=DTOMeta,
        metadata=MetaData(
            schema="postgres",
        ),
    )
