import sys

from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

from ecosim_hpc.tech.db.db_types import DTOMeta
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_hpc.config.cli_arguments import CLIArguments as HPCArguments

if "ecosim_hpc.client_manager" in sys.modules:
    SimControlDB_Base = declarative_base(
        metaclass=DTOMeta,
        metadata=MetaData(
            schema=HPCArguments().db_config_overwrite().schema(default="ERROR_NO_SCHEMA"),
        ),
    )

elif "pytest" not in sys.modules:
    SimControlDB_Base = declarative_base(
        metaclass=DTOMeta,
        metadata=MetaData(
            schema=CLIArguments().db_config_overwrite().schema(default="ERROR_NO_SCHEMA"),
        ),
    )

else:
    SimControlDB_Base = declarative_base(
        metaclass=DTOMeta,
        metadata=MetaData(
            schema="postgres",
        ),
    )
