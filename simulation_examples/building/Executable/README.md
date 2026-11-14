# Building example with PostgreSQL

Couples the weather, occupancy and house models for 100 steps of 15 minutes and stores the results
in PostgreSQL.

**Warning: every start of `serverRun.sh` drops the schema `temp_schema` in the database
`sim_control` with all its tables, so the results of the previous run are lost. Only a start with
`--restore-simulation-run` keeps them.**

You need [uv](https://docs.astral.sh/uv/), a PostgreSQL server and Linux. The models have no macOS
binaries and the scripts need bash.

## 1. Get the source

```shell
git clone https://github.com/KIT-IAI-ESA/ecosim.git
cd ecosim/simulation_examples/building/Executable
```

## 2. Check the database encoding

The server creates the database `sim_control` if it is missing, if your database user is allowed to,
with the default encoding of the PostgreSQL cluster. The server stops with an error on `SQL_ASCII`,
the default of a cluster created with the `C` locale. In that case, create the database yourself:

```shell
createdb --host localhost --username postgres --encoding UTF8 --template template0 sim_control
```

## 3. Start the server

```shell
PGPASSWORD=<password> ./serverRun.sh --database-host localhost --database-user postgres
```

The first run creates the environment, which takes a moment. The server then waits for the clients.
Instead of these settings you can fill in the `[database]` section of `../server/preferences.ini`.

## 4. Start the clients

In a second terminal, in the same folder:

```shell
./moduleRun.sh
```

The clients retry connecting for 30 seconds. When the simulation is finished, the server and the
clients exit.

## 5. Look at the results

```shell
psql --host localhost --username postgres --dbname sim_control
```

```sql
\dt temp_schema.*
SELECT timestamp, o_t_indoor FROM temp_schema.module_house ORDER BY timestamp LIMIT 5;
```

`module_house`, `module_occupancy` and `module_weather` have one row per step, `simulation_state`
says `finished`.

## Options

Both scripts pass extra arguments on, `moduleRun.sh` to each of the three clients:

| Purpose | Server | Clients |
| --- | --- | --- |
| Another server port, the default is 1234 | `--port 1235` | `--server-port 1235` |
| Every message, also one for each step | `--debug` | `--debug` |
| Fewer steps | `--steps 10` | |
| Another database port, the default is 5432 | `--database-port 5433` | |
| Another schema, also dropped if it exists | `--database-schema my_run` | |

To run without PostgreSQL, write the results as files instead:
`./serverRun.sh --database-type file --database-directory results`. The
[quick start](../../../docs/content/getting-started/quick-start.md) runs this example with one
command, `uv run ecosim run building --steps 100` in `simulation_examples`, with the results as files.

All options are in the [command-line reference](../../../docs/content/reference/command-line.md).
