# eCoSim docker example

Runs the *house* simulation with one server and four FMU v2 clients in containers:

```
weather ──T_out, dir_sol_irradiance──▶ house ──room_temperature──▶ heating ─────┐
                                        ▲                          ventilation ─┘
                                        └──── control signals ──────────────────┘
```

The models come from `ecosim-test-common`: `ecosim_test_common/resources/fmu_v2/models/house/linux`.

## Prerequisites

Build the images once - they are tagged `localhost/ecosim_*`:

```shell
docker compose -f ../docker-compose-build-images.yml build ecosim_server ecosim_client_fmu_v2
```

## Run

```shell
docker compose up --abort-on-container-exit
```

The run takes a few seconds. It is finished when the server prints `SERVER MEASUREMENT`
and every container has exited with code 0.

## Check the results

The database container is kept, so the results can be queried after the run:

```shell
podman start ecosim-example-db
podman exec ecosim-example-db psql -U postgres -d postgres \
  -c "SELECT state FROM ecosim_example.simulation_state;" \
  -c "SELECT * FROM ecosim_example.module_house LIMIT 5;"
```

Expected: state `finished` and one row per simulation step in each `module_*` table.

## Clean up

```shell
docker compose down -v
```

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | db, server and the four clients |
| `config/server_config.ini` | server port and database connection |
| `config/simulation.json` | the simulators and how their interfaces are connected |

## Notes

- The `*_preferences_linux.ini` next to the models point at `localhost:1234`. The clients
  override this with `--server-host=server`, so the shared resources stay untouched.
- The server writes into the database `postgres` and the schema `ecosim_example`.
  A dedicated database is not used because the server connects to `--database-name` to
  create a missing database, which only works for a database that already exists.
- `--database-drop-existing-schema` makes the example repeatable. Without it the server
  aborts when the schema of a previous run is still present.
- The clients retry the connect for 30s, so plain `depends_on` is enough to start them
  together with the server.
