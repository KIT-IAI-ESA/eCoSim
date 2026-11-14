---
title: Read the results
description: Look at the results of a run, write them to a CSV file, or read them in Python.
---

# Read the results

`ecosim results` shows what a run stored, and writes it as one table to a CSV file. The commands below run in
`simulation_examples`, after a run of [Run a simulation](run-a-simulation.md).

## What a run stores

A run of `ecosim run` keeps its results in its run folder, like `building/results/2026-11-14_15-13-51`. The
server writes the same files into the folder of `--database-directory` when you start it by hand.

| File | Content |
| --- | --- |
| `module_<simulator>.jsonl` | one line for each step, with the outputs of the simulator and the inputs it got |
| `simulation_state.jsonl` | the states of the run, ending with `{"state": "Finished"}` |
| `server_time_measurement.jsonl` | how long the server took |
| `simulation.json` | a copy of the simulation config of the run, which says which values are inputs |

In PostgreSQL, a run writes into its schema one table `module_<simulator>` for each simulator, and the tables
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

- `Results` is the folder it read. For a simulation folder it is the newest run folder in its `results/`.
- `Run` is the state of the run and how many steps it stored. A run that ended with Ctrl-C or a failed part says
  `failed`.
- `Simulated` is the simulated time, from the start date to the end of the last step.
- `Columns` counts the columns of the table. The inputs are left out, since each one is a copy of the output it is
  connected to. `--inputs` shows them.

The folder can be a simulation folder, a run folder, or any folder of result files, like `building/Executable/results` of a
server that you started by hand. Without a folder, `ecosim results` reads the current folder.

## Write the results to a CSV file

```shell
uv run ecosim results building --interface house.T_indoor --interface weather.weatherBus.TDryBul --csv temperatures.csv
```

```text
time,house.T_indoor,weather.weatherBus.TDryBul
2023-01-01T00:15:00+00:00,292.2132952042424,271.1328125
2023-01-01T00:30:00+00:00,291.8940263529693,271.12916666666666
```

- one row for each step. The time is the end of the step, with its offset to UTC.
- one column for each interface, named after the simulator and the interface. An array gets a column for each
  position, like `source.y[0]` and `source.y[1]`.
- a comma between the columns and a point in the numbers, which keep all their digits. A missing value is an empty
  cell.
- `--interface` takes a column, a simulator like `house`, or an array like `source.y`, and can be given more than
  once. The columns come in the order of the names. A misspelt name gets the closest one as a hint.
- without `--interface`, the file has every column of the overview, and with `--inputs` the inputs too.

To read the file:

- pandas: `pandas.read_csv("temperatures.csv", index_col="time", parse_dates=["time"])`
- MATLAB: `readtable("temperatures.csv", "VariableNamingRule", "preserve")`, which keeps the dots in the names
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

`read_file_results` takes a folder of result files, so for `ecosim run` a run folder, not the simulation folder. It leaves out the
inputs unless you pass `include_inputs=True`. For a folder without a copy of `simulation.json`, pass
`simulation_config="building/server/simulation.json"`. `table.select(names=["house"])` keeps the columns that the
names pick, as `--interface` does. `to_pandas_data_frame()` needs pandas, which comes with the extra `ecosim[pandas]`, and
`simulation_examples` has it.

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

`--server-config` takes the place of the folder. The `[database]` section of the server config says where the
results are, and the `--database` options change it, with the same names and meaning as for `ecosim-server`.
`ecosim results` takes them itself, so they come without the `--` that `ecosim run` needs before them. So for a
server you started by hand, give its server config and the `--database` options of its run. The password
comes from the server config, `--database-user-password`, `PGPASSWORD` or a password file, as for the server. The
printed command leaves out `--database-user-password`, so that the password does not show on the screen.

- PostgreSQL keeps the names in lower case. Without `--simulation-config`, the columns are named like
  `house.t_indoor`, and `--interface house.T_indoor` still finds them. The copy of `simulation.json` in the run
  folder gives the names as they are written there.
- The times come in UTC. With a start date in another time zone, the table of the files keeps that offset, and the
  table from PostgreSQL shows the same moments in UTC.
- On an HPC cluster, read the results while the PostgreSQL server of the job runs, see
  [HPC cluster](hpc-cluster.md#look-at-the-results).

## More than one run in a folder

The server adds a run to the files that are already in its `--database-directory`. `ecosim run` gives each run a
folder of its own, so this only happens when you start the server yourself twice with the same folder. Then
`ecosim results` shows the last run and says so:

```text
results holds 2 runs, because the server adds each run to the files of the earlier ones. The table shows the last run. Delete the folder before a run, or give each run its own --database-directory.
```

## The stored format

For your own tools, each line of `module_<simulator>.jsonl` is one JSON object for one step, with the values of the
outputs and then of the inputs, and the time at the end of the step:

```json
{"values": [{"name": "T_indoor", "value": 292.2132952042424}], "timestamp": "2023-01-01T00:15:00+00:00"}
```

An array is a JSON list. In PostgreSQL the table of a simulator has the column `timestamp`, a column `o_<name>`
for each output and `i_<name>` for each input, all in lower case, and next to each one a column ending in `_json`,
which holds the value if it is an array.
