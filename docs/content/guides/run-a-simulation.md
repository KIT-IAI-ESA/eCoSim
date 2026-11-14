---
title: Run a simulation
description: Check a simulation and run it on this computer with one command.
---

# Run a simulation

A simulation folder holds the config files of the server and one folder for each simulator:

```text
building/
  server/
    simulation.json    the simulators, their connections, the step size and the start date
    preferences.ini    the server config
  Modules/
    house/             the client config, the .fmc file and the model of one simulator
    occupancy/
    weather/
  results/             a folder for each run, which ecosim run writes
```

`simulation_examples/building` has this layout. The commands below run in `simulation_examples`, where `uv run`
finds the `ecosim` command. For a simulation folder with another layout, `--simulation-config`, `--server-config` and
`--simulator-dir` name the files one by one.

## Check the simulation

```shell
uv run ecosim check building
```

```text
Checked building: 3 simulators, no problems.
  house      FMI 2.0  building/Modules/house      18 inputs   6 outputs
  occupancy  FMI 2.0  building/Modules/occupancy   0 inputs   7 outputs
  weather    FMI 2.0  building/Modules/weather     0 inputs  11 outputs
```

`ecosim check` reads the simulation the way a run reads it, with the readers of the server and the clients, and starts
no part of a run. It imports a Python model in a Python process of its own, as its client does at its start. It lists
every problem with its file, not only the first one, and names the closest name for a typo:

```text
Checked building: 2 simulators, 1 problem.
  occupancy  FMI 2.0  building/Modules/occupancy  0 inputs   7 outputs
  weather    FMI 2.0  building/Modules/weather    0 inputs  11 outputs
Problems:
  building/Modules/house/preferences.ini: simulator_name is 'hous', but building/server/simulation.json has no simulator 'hous'. Did you mean house?
Fix it and run the check again: uv run ecosim check building
```

A problem stops a run, a warning does not. A key that nothing reads gives a warning, and so does a port that only
matters when the parts are started by hand. The check ends with exit code 1 if it found a problem, else with 0.
A command that `ecosim` prints for you to copy starts the way you started `ecosim`, with `uv run` in
`simulation_examples`.
With the options of a run, like `--steps` or `--database-type postgres`, it checks that run. Check a simulation before
an HPC job too, see [HPC cluster](hpc-cluster.md).

## Run it

```shell
uv run ecosim run building --steps 100
```

```text
Checked building: 3 simulators, no problems.
Run 2026-11-14_12-59-25: 100 steps of 15 min, from 2023-01-01 00:00 to 2023-01-02 01:00 UTC.
Started the server and 3 clients. Logs: building/results/2026-11-14_12-59-25/logs
Finished after 2.5 s. Results: files in building/results/2026-11-14_12-59-25
```

`ecosim run` checks the simulation, picks a free port, starts the server and a client for each simulator and waits until
the server has finished. A longer run shows a progress line every 10 seconds in the first minute, then every minute
and after an hour every 10 minutes. The length of the run comes from
`--steps`, from `--duration`, like `--duration 365d`, or from `steps` in the setup of `simulation.json`.
`--step-size 15min` overrides `setup.delta_t`. A step size without a unit is in milliseconds, as for the server.

The model of a simulator chooses its client: the Python client if its client config has `model` in `[python]`, else
the FMI 2.0 or FMI 3.0 client for an `.fmu` file, the MATLAB client for `.m` files and the Pyro5 client for a `.py`
file.

## The run folder

Each run gets a folder of its own in `results/` of the simulation, named after its start time, so a second run never adds
to the first one. `--results FOLDER` sets the folder.

| In the run folder | Content |
| --- | --- |
| `module_<simulator>.jsonl` | the outputs of a simulator, one line for each step |
| `simulation_state.jsonl` | the states of the run, ending with `{"state": "Finished"}` |
| `server_time_measurement.jsonl` | how long the server took |
| `simulation.json` | a copy of the simulation config of the run |
| `logs/server.log`, `logs/<simulator>.log` | everything each part printed |

The warnings of a model, like those of the house FMU at its first step, are only in its log. With `--debug` the logs
have every message, also one for each step.

`--database-type postgres` stores the results in PostgreSQL with the `[database]` section of the server config, and
the run folder holds only the logs and the copy of `simulation.json`. Options of `ecosim-server` that `ecosim run`
has no option for go after `--`:

```shell
uv run ecosim run building --steps 100 --database-type postgres -- --database-schema run_2
```

Each PostgreSQL run needs a schema of its own. The server stops if the schema is there from an earlier run, so give
every run a new name with `--database-schema`, or add `--database-drop-existing-schema` to replace the old results.

## Stop and continue a run

Ctrl-C stops the server and every client. A second Ctrl-C a few seconds later kills them. The last line says how to
continue the run:

```text
Stopping the run. Press Ctrl-C again to kill it.
Stopped after 2.5 s. The results so far: files in building/results/2026-11-14_13-00-29
Continue the run with: uv run ecosim run building --steps 20000 --restore-simulation-run
```

`--restore-simulation-run` continues the newest run in `results/` of the simulation, or the run in the folder that
`--results` names. The config files must not change in between. If `simulation.json` did, the run says so and names
the copy of the old one in the run folder.

When one part fails, the run shows the warnings of the server, why the part failed, and stops the other parts:

```text
server: Client house#house closed the connection
server: The run failed: Lost client house#house while waiting for all clients to start their simulation -> closing the client connections and the server
house stopped with exit code 1. The end of building/results/2026-11-14_14-25-37/logs/house.log:
    The simulation config does not fit the model. The FMU building/Modules/house/house.fmu has no input weatherBus_TDryBull. Did you mean weatherBus_TDryBul? This client does not start the simulation.
    house#house did not start the simulation. The error above says why.
Stopping the server and the other clients.
Failed after 2.0 s. The results so far: files in building/results/2026-11-14_14-25-37
```

The check finds this mistake before anything starts. `--no-check` starts the run without it.

| Exit code | When |
| --- | --- |
| 0 | the run finished |
| 1 | a part failed, or the check found a problem |
| 2 | an option is missing or has a wrong value |
| 33 | Ctrl-C stopped the run |
| 44 | a terminate signal stopped the run, for example from `kill` |

Each part also ends with its exit code, 33 after a Ctrl-C. On Windows a stop reaches the parts as a break signal, so
there each part ends with 44, also after a Ctrl-C. `ecosim run` itself still ends with 33.

## MATLAB, Pyro5 and Python models

`ecosim run` starts the FMU clients and the Python client with the Python of its own environment. A package that a
Python model imports has to be installed there, or be added for one run with `uv run --with pandapower ecosim run ...`.

The MATLAB client needs Python 3.12, so it usually has an environment of its own. `ecosim run` finds
`ecosim-client-matlab` on the PATH, see [MATLAB client](matlab-client.md). It knows a MATLAB model by the `.m` files
in the simulator folder, so the scripts sit there for `ecosim check` and `ecosim run`. The Pyro5 client comes with
the extra `ecosim[pyro5]`. `ecosim run` does not start the Pyro5 object, so start it first, see
[Pyro5 client](pyro5-client.md). If nothing listens on `pyro_host` and `pyro_port` of the client config, the check
before the run stops it.

## Start the parts by hand

For a run on several machines, start the server and each client yourself. In `building/Executable`:

```shell
# terminal 1
uv run --project ../.. ecosim-server --server-config ../server/preferences.ini \
    --simulation-config ../server/simulation.json --steps 100 \
    --database-type file --database-directory results
# terminal 2
for module in house occupancy weather; do
    uv run --project ../.. ecosim-client-fmu-v2 --config-file "../Modules/$module/preferences.ini" &
done
wait
```

Each client config then needs `ip` and `port` of the server in its `[server]` section. The clients try to connect
for 30 seconds, so they can start right after the server. `serverRun.sh` and `moduleRun.sh` in the same folder start
the same parts, with the results in PostgreSQL.
