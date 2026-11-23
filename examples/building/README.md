# Building example

A house, its weather and the people in it, as three FMI 2.0 models. In every step of 15 minutes `weather`
and `occupancy` give their values to `house`.

Run it from the `examples` folder. The results are written as files, so no database is needed:

```shell
uv run ecosim run building --steps 100
uv run ecosim results building
```

The [quick start](../../docs/content/getting-started/quick-start.md) explains each step.

## Start the server and the clients by hand, with PostgreSQL

`run-server.sh` and `run-clients.sh` in this folder start the server and the three clients by hand. They run
100 steps of 15 minutes and store the results in PostgreSQL.

**Warning: every start of `run-server.sh` drops the schema `temp_schema` in the database
`sim_control` with all its tables, so the results of the previous run are lost. Only a start with
`--restore-simulation-run` keeps them.**

You need [uv](https://docs.astral.sh/uv/), a PostgreSQL server and Linux. The models have no macOS
binaries and the scripts need bash.

### 1. Get the source

```shell
git clone https://github.com/KIT-IAI-ESA/ecosim.git
cd ecosim/examples/building
```

### 2. Check the database encoding

The server creates the database `sim_control` if it is missing, if your database user is allowed to,
with the default encoding of the PostgreSQL cluster. The server stops with an error on `SQL_ASCII`,
the default of a cluster created with the `C` locale. In that case, create the database yourself:

```shell
createdb --host localhost --username postgres --encoding UTF8 --template template0 sim_control
```

### 3. Start the server

```shell
PGPASSWORD=<password> ./run-server.sh --database-host localhost --database-user postgres
```

The first run creates the environment, which takes a moment. The server then waits for the clients.
Instead of these settings you can fill in the `[database]` section of `server/preferences.ini`.

### 4. Start the clients

In a second terminal, in the same folder:

```shell
./run-clients.sh
```

The clients retry connecting for 30 seconds. When the simulation is finished, the server and the
clients exit.

### 5. Look at the results

```shell
psql --host localhost --username postgres --dbname sim_control
```

```sql
\dt temp_schema.*
SELECT timestamp, o_t_indoor FROM temp_schema.module_house ORDER BY timestamp LIMIT 5;
```

`module_house`, `module_occupancy` and `module_weather` have one row per step, `simulation_state`
says `finished`.

### Options

Both scripts pass extra arguments on, `run-clients.sh` to each of the three clients:

| Purpose | Server | Clients |
| --- | --- | --- |
| Another server port, the default is 1234 | `--port 1235` | `--server-port 1235` |
| More logs | `--debug` | `--debug` |
| Fewer steps | `--steps 10` | |
| Another database port, the default is 5432 | `--database-port 5433` | |
| Another schema, also dropped if it exists | `--database-schema my_run` | |

To run without PostgreSQL, write the results as files instead:
`./run-server.sh --database-type file --database-directory results/manual`

All options are in the [command-line reference](../../docs/content/reference/command-line.md).
