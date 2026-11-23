---
title: Read the results
description: Look at the results of a run, write them to a CSV file, or read them in Python.
---

# Read the results

`ecosim results` shows the results of a run and writes them as one table to a CSV file. The commands below run in
`examples`, after a run of [Run a simulation](run-a-simulation.md).

## What a run stores

`ecosim run` writes the results to the run folder, like `building/results/2026-11-14_15-13-51`. A server that you
start manually writes the same files to its `--database-directory`.

| File | Content |
| --- | --- |
| `module_<simulator>.jsonl` | one line per step with the outputs of the simulator and the inputs it got |
| `simulation_state.jsonl` | the states of the run, ending with `{"state": "Finished"}` |
| `server_time_measurement.jsonl` | how long the server took |
| `simulation.json` | a copy of the simulation config of the run |

In PostgreSQL a run writes one table `module_<simulator>` per simulator into its schema, and the tables
`simulation_state` and `server_time_measurement`.

## Look at a run

```shell
uv run ecosim results building
```

```text
Results:     building/results/2026-11-14_15-13-51
Run:         finished, 100 steps of 15 min
Simulated:   2023-01-01 00:00 to 2023-01-02 01:00 UTC
Simulators:  house, occupancy, weather
Columns:     24 outputs, 18 inputs are left out (add --inputs)

Column                                         Minimum          Mean       Maximum
house.T_indoor                                  291.14       293.752       295.001
house.Pe_gen                                         0             0             0
house.Pe_load                                 -485.435      -426.473      -182.925
...
weather.weatherBus.solZen                      1.25799       1.94552       2.68866

Add --csv results.csv to write the table to a file.
```

For a simulation folder it shows the newest run in `results/`. A run that was stopped or failed shows `failed` in
the `Run` line. The inputs are left out. Each input is a copy of the output it is connected to. `--inputs` shows
them.

The folder can also be a run folder or any folder with result files, like `building/results/manual` of a
server that you started manually. Without a folder `ecosim results` reads the current folder.

## Write the results to a CSV file

```shell
uv run ecosim results building --interface house.T_indoor --interface weather.weatherBus.TDryBul --csv temperatures.csv
```

```text
time,house.T_indoor,weather.weatherBus.TDryBul
2023-01-01T00:15:00+00:00,292.2132952042424,271.1328125
2023-01-01T00:30:00+00:00,291.8940263529693,271.12916666666666
```

- one row per step. The time is the end of the step with its offset to UTC
- one column per interface, named after the simulator and the interface. An array gets one column per position,
  like `source.y[0]` and `source.y[1]`
- `--interface` takes a column, a simulator like `house` or an array like `source.y`. It can be given several times
- without `--interface` the file has every column of the overview, with `--inputs` the inputs too

To read the file:

- pandas: `pandas.read_csv("temperatures.csv", index_col="time", parse_dates=["time"])`
- MATLAB: `readtable("temperatures.csv", "VariableNamingRule", "preserve")` keeps the dots in the names
- Excel: Data > From Text/CSV

## In Python

```python
from ecosim_server.results import read_file_results

table = read_file_results("building/results/2026-11-14_15-13-51")
table.column_names()                  # ('house.T_indoor', 'house.Pe_gen', ...)
table.simulation_times                # the end of each step, as a datetime with its time zone
table.values("house.T_indoor")        # [292.2132952042424, 291.8940263529693, ...]
frame = table.to_pandas_data_frame()  # a pandas DataFrame with the simulation times as index
```

`read_file_results` takes a folder with result files. For `ecosim run` that is a run folder, not the simulation folder.
It leaves out the inputs unless you pass `include_inputs=True`. `table.select(names=["house"])` keeps the columns
of the house, like `--interface`. `to_pandas_data_frame()` needs pandas. It comes with the extra `ecosim[pandas]` and
`examples` has it.

## Results in PostgreSQL

At the end of a run with `--database-type postgres`, `ecosim run` prints the command that reads its results:

```shell
uv run ecosim run building --steps 20 --database-type postgres -- --database-host localhost --database-schema run_2
```

```text
...
Finished after 2.0 s. Results: PostgreSQL database sim_control on localhost:5432, schema run_2
Read them with: uv run ecosim results --server-config building/server/preferences.ini --simulation-config building/results/2026-11-14_15-16-09/simulation.json --database-type postgres --database-host localhost --database-schema run_2
```

`--server-config` takes the place of the folder. The `[database]` section of the server config tells where the
results are. The `--database` options override it, as for `ecosim-server`. Here they come without the `--` that
`ecosim run` needs before them. For a server you started manually, pass its server config and the `--database`
options of its run. The password comes from the server config, `PGPASSWORD` or a password file.

PostgreSQL stores the names in lower case. Without `--simulation-config` the columns are named like
`house.t_indoor`. The times are in UTC.

On an HPC cluster, read the results while the PostgreSQL server of the job runs, see
[HPC cluster](hpc-cluster.md#look-at-the-results).

## More than one run in a folder

The server adds a run to the files that are already in its `--database-directory`. With `ecosim run` this does not
happen. If you start the server yourself twice with the same folder, `ecosim results` shows the last run and prints
a warning:

```text
results contains 2 runs. The table shows the last run. Delete the folder before a run or use a separate --database-directory per run.
```

## The stored format

For your own tools, each line of `module_<simulator>.jsonl` is one JSON object for one step. It has the values of
the outputs, then the values of the inputs and the time at the end of the step:

```json
{"values": [{"name": "T_indoor", "value": 292.2132952042424}], "timestamp": "2023-01-01T00:15:00+00:00"}
```

An array is a JSON list. In PostgreSQL the table of a simulator has the column `timestamp`, a column `o_<name>`
per output and `i_<name>` per input, all in lower case. An array value is in a second column ending in `_json`.
