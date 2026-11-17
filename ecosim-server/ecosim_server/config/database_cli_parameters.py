from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.option_values import choice_name, port_number, true_or_false

RESULTS = "results"

DATABASE_PARAMETERS = (
    AppConfigParameter(
        name="database-type",
        group=RESULTS,
        transform=choice_name,
        choices=tuple(member.serialized for member in DatabaseType),
        help_text="Where the results go. Overrides type in the [database] section of the config file. "
        + f"If neither sets it, {DatabaseType.POSTGRES.serialized}.",
    ),
    AppConfigParameter(
        name="database-directory",
        group=RESULTS,
        metavar="FOLDER",
        help_text=f"The folder for the result files of --database-type {DatabaseType.FILE.serialized}. Overrides directory in the "
        + "[database] section of the config file. If neither sets it, simulation_results.",
    ),
    AppConfigParameter(
        name="database-host",
        group=RESULTS,
        metavar="HOST",
        help_text="The host of the PostgreSQL server. Overrides server in the [database] section of the config file.",
    ),
    AppConfigParameter(
        name="database-port",
        group=RESULTS,
        transform=port_number,
        metavar="PORT",
        help_text="The port of the PostgreSQL server. Overrides port in the [database] section of the config file.",
    ),
    AppConfigParameter(
        name="database-user",
        group=RESULTS,
        metavar="USER",
        help_text="The PostgreSQL user. Overrides username in the [database] section of the config file.",
    ),
    AppConfigParameter(
        name="database-user-password",
        group=RESULTS,
        metavar="PASSWORD",
        help_text="The password of the PostgreSQL user. Other users on a shared machine can see it in the process list. "
        + "Without it, the password comes from the config file, PGPASSWORD or a password file.",
    ),
    AppConfigParameter(
        name="database-name",
        group=RESULTS,
        metavar="NAME",
        help_text="The PostgreSQL database. Default: sim_control.",
    ),
    AppConfigParameter(
        name="database-schema",
        group=RESULTS,
        metavar="NAME",
        help_text="The PostgreSQL schema of the result tables. Default: sim_control.",
    ),
    AppConfigParameter(
        name="database-ssl",
        group=RESULTS,
        transform=true_or_false,
        metavar="{true,false}",
        help_text="true connects to PostgreSQL with sslmode=require, false with sslmode=disable. "
        + "Overrides ssl in the [database] section of the config file.",
    ),
    AppConfigParameter(
        name="database-drop-existing-schema",
        group=RESULTS,
        is_flag=True,
        help_text="Deletes the PostgreSQL schema of an earlier run with all its results. With --restore-simulation-run the schema is kept.",
    ),
)
