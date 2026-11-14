"""The ini sections of the server and the clients with their intro texts."""

SERVER_INTRO = r"""The ini file passed to `ecosim-server` with `--server-config`. Matching command-line options override these keys.
`ssl=true` connects with `sslmode=require`, `ssl=false` with `sslmode=disable`.

The `[database]` keys `server`, `port`, `ssl`, `username` and `password` are only read for results in PostgreSQL, the
default. For results as files (`type=file` or `--database-type file`) the section can be left out or have only `type`
and `directory`.

The database password comes from the first of these that has one:

1. `--database-user-password`
2. `password` in this file
3. the environment variable `PGPASSWORD`
4. the password file named by `PGPASSFILE`, by default `~/.pgpass`

The password file has lines of the form `host:port:database:username:password`, and PostgreSQL ignores it unless only you
can read it (mode `0600`). Write the database as `*`, because the server also connects to `postgres` to create a missing
database. In a password, write `:` as `\:` and `\` as `\\`.

:::warning

Other users on a shared machine can see `--database-user-password` in the process list. Use the password file there.

:::"""
GROUPS = [
    (
        "Server",
        SERVER_INTRO,
        "ecosim-server/ecosim_server/config/server_config.py",
    ),
    (
        "All clients",
        "The `preferences.ini` passed to a client with `--config-file`. `--server-host` and `--server-port` override the server keys. "
        "See [client types](#client-types) for `type`, [lists](#lists) for `fmc_file` and [interface files](#interface-files) for the file it names.",
        "ecosim-common/ecosim_common/client/config/client_config.py",
    ),
    (
        "FMU clients",
        "Read in addition by `ecosim-client-fmu-v2` and `ecosim-client-fmu-v3`. `fmu_file` is relative to the ini file. "
        "Both clients stop at start-up for an FMU of the other FMI version, for an input of the `.fmc` file that is not an input "
        "of the FMU, for an output of the `.fmc` file that is not an output of the FMU, and for a variable of a type they "
        "do not support. "
        "`--validate-fmu-file-only` reports all three. "
        "`ecosim-client-fmu-v2` supports Real variables only. "
        "`ecosim-client-fmu-v3` supports `Float64` variables only: "
        "scalars and one-dimensional arrays with a fixed size or a size from a structural parameter.",
        "ecosim-common-fmpy/ecosim_common_fmpy/config/fmu_base_config.py",
    ),
    (
        "MATLAB client",
        "Read in addition by `ecosim-client-matlab`. "
        "`scriptfolder` is relative to the ini file and has to hold `setup.m`, `step.m` and `finishing.m`.",
        "ecosim-client-matlab/ecosim_client_matlab/matlab_config.py",
    ),
    (
        "Pyro5 client",
        "Read in addition by `ecosim-client-pyro5`.",
        "ecosim-client-pyro5/ecosim_client_pyro5/pyro_config.py",
    ),
    (
        "Python client",
        "Read in addition by `ecosim-client-python`. `model` names the module and the class of the model, "
        "for example `room:Room`. The folder of the ini file is searched first, then the installed packages. "
        "See the [Python client](../guides/python-client.md) guide.",
        "ecosim-client-python/ecosim_client_python/python_config.py",
    ),
]
