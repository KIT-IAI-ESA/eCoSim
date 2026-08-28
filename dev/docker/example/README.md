# eCoSim docker example

Runs the *house* simulation with one server and four FMU v2 clients in containers:

```
weather ──T_out, dir_sol_irradiance──▶ house ──room_temperature──▶ heating ─────┐
                                        ▲                          ventilation ─┘
                                        └──── control signals ──────────────────┘
```

The models come from `ecosim-test-common`: `ecosim_test_common/resources/fmu_v2/models/house/linux`.

There are two variants of the same simulation. They differ only in where the server
stores its results:

| Variant | Results are stored in | Directory |
| --- | --- | --- |
| `postgres` | a TimescaleDB container | `postgres/` |
| `file` | JSON lines on the host, no database needed | `file/` |

## Prerequisites

Build the images once - they are tagged `localhost/ecosim_*`:

```shell
docker compose -f ../docker-compose-build-images.yml build ecosim_server ecosim_client_fmu_v2
```

## Variant: postgres

```shell
cd postgres
docker compose up --abort-on-container-exit
```

The run takes a few seconds. It is finished when the server prints `SERVER MEASUREMENT`
and every container has exited with code 0.

### Check the results

The database container is kept, so the results can be queried after the run:

```shell
docker start ecosim-example-db
docker exec ecosim-example-db psql -U postgres -d postgres \
  -c "SELECT state FROM ecosim_example.simulation_state;" \
  -c "SELECT * FROM ecosim_example.module_house LIMIT 5;"
```

Expected: state `finished` and one row per simulation step in each `module_*` table.

### Clean up

```shell
docker compose down -v
```

## Variant: file

```shell
cd file
docker compose up --abort-on-container-exit
```

Same run, but without a database service - so nothing has to be started or waited for
besides the server itself.

### Check the results

The server writes into `/results`, which is mounted to `file/results` on the host, so
the results are plain files that can be read without any client:

```shell
ls results
head -n 1 results/module_house.jsonl
cat results/simulation_state.jsonl
```

Expected: one `module_*.jsonl` per simulator, each with one line per simulation step
(60 lines for `--steps=60`), a `server_time_measurement.jsonl` with the runtimes the
server prints as `SERVER MEASUREMENT`, and a `simulation_state.jsonl` that ends with
`{"state": "Finished"}`.

Every line is one JSON object - a measurement of the `house` simulator looks like this
(shortened to one interface):

```json
{"values": [{"name": "room_temperature", "value": 293.1350272259126}], "timestamp": "2024-01-01T00:01:00+00:00"}
```

### Clean up

```shell
docker compose down
rm -rf results
```

## Files

| File | Purpose |
| --- | --- |
| `<variant>/docker-compose.yml` | the server and the four clients (plus the db in `postgres`) |
| `<variant>/config/server_config.ini` | server port and where the results are stored |
| `<variant>/config/simulation.json` | the simulators and how their interfaces are connected |

`simulation.json` is identical in both variants - what is simulated does not depend on
where the results end up.

## Notes

- The `*_preferences_linux.ini` next to the models point at `localhost:1234`. The clients
  override this with `--server-host=server`, so the shared resources stay untouched.
- The clients retry the connect for 30s, so plain `depends_on` is enough to start them
  together with the server.
- The executable is the `ENTRYPOINT` of the images, so `command:` only lists arguments -
  they are appended to it. `docker run localhost/ecosim_server:latest --help` works the
  same way.
- Both variants publish port `1234`, so they cannot run at the same time.

### postgres

- The server writes into the database `postgres` and the schema `ecosim_example`.
  A dedicated database is not used because the server connects to `--database-name` to
  create a missing database, which only works for a database that already exists.
- `--database-drop-existing-schema` makes the example repeatable. Without it the server
  aborts when the schema of a previous run is still present.

### file

- `type=file` and `directory=/results` in `server_config.ini` select the file based
  repositories. `--database-type=file` and `--database-directory=...` do the same on the
  command line.
- The `[database]` keys `server`, `port`, `username`, `password` and `ssl` are read even
  for `type=file`, so they are present but empty.
- The repositories append to their files, so a second run adds its results to the ones
  that are already there. Delete `results` in between to start clean.
- The server container runs as root, so with a rootful docker daemon the files in
  `results` belong to root. Rootless podman maps them to the calling user.
