---
title: Run a simulation
description: Check a simulation and run it locally with one command.
---

# Run a simulation

A simulation folder has the config files of the server and one folder per simulator:

```text
building/
  server/
    simulation.json    the simulators, their connections, the step size and the start date
    preferences.ini    the server config
  modules/
    house/             the client config, the .fmc file and the model of one simulator
    occupancy/
    weather/
  results/             one folder per run of ecosim run
```

`examples/building` has this layout. Older simulations with `Modules/` instead of `modules/` work as well.
The commands below run in `examples`. For another layout, pass the files with `--simulation-config`,
`--server-config` and `--simulator-dir`.

## Check the simulation

```shell
uv run ecosim check building
```

```text
Checked building: 3 simulators, no problems.
  house      FMI 2.0  building/modules/house      18 inputs   6 outputs
  occupancy  FMI 2.0  building/modules/occupancy   0 inputs   7 outputs
  weather    FMI 2.0  building/modules/weather     0 inputs  11 outputs
```

`ecosim check` reads the simulation like a run does and starts nothing. It lists every problem with its file and
suggests the closest name for a typo:

```text
Checked building: 2 simulators, 1 problem.
  occupancy  FMI 2.0  building/modules/occupancy  0 inputs   7 outputs
  weather    FMI 2.0  building/modules/weather    0 inputs  11 outputs
Problems:
  building/modules/house/preferences.ini: simulator_name is 'hous', but building/server/simulation.json has no simulator 'hous'. Did you mean house?
Fix it and run the check again: uv run ecosim check building
```

A problem stops a run, a warning does not. An unknown key is a warning. The exit code is 1 if the check found a
problem, else 0. With the options of a run, like `--steps` or `--database-type postgres`, it checks that run.
Check a simulation before an HPC job too, see [HPC cluster](hpc-cluster.md).

## Run it

```shell
uv run ecosim run building --steps 100
```

```text
Checked building: 3 simulators, no problems.
Run 2026-11-14_12-59-25: 100 steps of 15 min, from 2023-01-01 00:00 to 2023-01-02 01:00 UTC.
Started the server and 3 clients. Logs: building/results/2026-11-14_12-59-25/logs
Finished after 2.5 s. Results: files in building/results/2026-11-14_12-59-25
Read them with: uv run ecosim results building
```

`ecosim run` checks the simulation, picks a free port and starts the server and one client per simulator. A longer
run shows a progress line from time to time. The length of the run comes from `--steps`, from `--duration`, like
`--duration 365d`, or from `steps` in the setup of `simulation.json`. `--step-size 15min` overrides `setup.delta_t`.

The files in a simulator folder decide which client runs it:

| In the simulator folder | Client |
| --- | --- |
| `model` in `[python]` of the client config | Python client |
| an `.fmu` file | FMI 2.0 or FMI 3.0 client |
| `.m` files | MATLAB client |
| a `.py` file | Pyro5 client |

## The run folder

Each run gets its own folder in `results/` of the simulation, named after its start time. `--results FOLDER` sets
another folder.

| In the run folder | Content |
| --- | --- |
| `module_<simulator>.jsonl` | the outputs of a simulator, one line per step |
| `simulation_state.jsonl` | the states of the run, ending with `{"state": "Finished"}` |
| `server_time_measurement.jsonl` | how long the server took |
| `simulation.json` | a copy of the simulation config of the run |
| `logs/server.log`, `logs/<simulator>.log` | the output of the server and of each client |

`ecosim results building` shows the results of the newest run, see [Read the results](results.md).

The warnings of a model, like those of the house FMU in its first step, are only in its log. `--debug` adds the
debug messages to the logs.

`--database-type postgres` stores the results in PostgreSQL with the `[database]` section of the server config.
The run folder then has only the logs and the copy of `simulation.json`. Options of `ecosim-server` that
`ecosim run` does not have go after `--`:

```shell
uv run ecosim run building --steps 100 --database-type postgres -- --database-schema run_2
```

Each PostgreSQL run needs its own schema. The server stops if the schema exists from an earlier run. Use a new
name with `--database-schema` or replace the old results with `--database-drop-existing-schema`. To read the
results, see [Results in PostgreSQL](results.md#results-in-postgresql).

## Stop and continue a run

Ctrl-C stops the server and every client. A second Ctrl-C a few seconds later kills them. The last line shows how
to continue the run:

```text
Stopping the run. Press Ctrl-C again to kill it.
Stopped after 2.5 s. The results so far: files in building/results/2026-11-14_13-00-29
Continue the run with: uv run ecosim run building --steps 20000 --restore-simulation-run
```

`--restore-simulation-run` continues the newest run in `results/` of the simulation, or the run in the `--results`
folder. The config files must not change in between.

When the server or a client fails, the run shows why and stops the others:

```text
server: Client house#house closed the connection
server: The run failed: Lost client house#house while waiting for all clients to start their simulation -> closing the client connections and the server
house stopped with exit code 1. The end of building/results/2026-11-14_14-25-37/logs/house.log:
    The simulation config does not fit the model. The FMU building/modules/house/house.fmu has no input weatherBus_TDryBull. Did you mean weatherBus_TDryBul? This client does not start the simulation.
    house#house did not start the simulation. The error above says why.
Stopping the server and the other clients.
Failed after 2.0 s. The results so far: files in building/results/2026-11-14_14-25-37
```

The check finds this mistake before anything starts. `--no-check` starts the run without it.

| Exit code | When |
| --- | --- |
| 0 | the run finished |
| 1 | the server or a client failed, or the check found a problem |
| 2 | an option is missing or has a wrong value |
| 33 | Ctrl-C stopped the run |
| 44 | a terminate signal stopped the run, for example from `kill` |

## MATLAB, Pyro5 and Python models

`ecosim run` starts the FMU clients and the Python client with the Python of its environment. A package that a
Python model imports has to be installed there. For one run, add it with `uv run --with pandapower ecosim run ...`.

The MATLAB client needs Python 3.12 and usually has its own environment. `ecosim run` looks for
`ecosim-client-matlab` on the PATH, see [MATLAB client](matlab-client.md). The `.m` files have to be in the
simulator folder.

The Pyro5 client comes with the extra `ecosim-cli[pyro5]`. `ecosim run` does not start the Pyro5 object. Start it
first, see [Pyro5 client](pyro5-client.md). The check before the run stops if nothing listens on `pyro_host` and
`pyro_port` of the client config.

## Start the server and the clients manually

For a run on several machines, start the server and each client yourself. In `building`:

```shell
# terminal 1
uv run --project .. ecosim-server --server-config server/preferences.ini \
    --simulation-config server/simulation.json --steps 100 \
    --database-type file --database-directory results/manual
# terminal 2
for module in house occupancy weather; do
    uv run --project .. ecosim-client-fmu-v2 --config-file "modules/$module/preferences.ini" &
done
wait
```

Each client config then needs `ip` and `port` of the server in its `[server]` section. The clients try to connect
for 30 seconds. `serverRun.sh` and `moduleRun.sh` in the same folder do the same with the results in PostgreSQL.
