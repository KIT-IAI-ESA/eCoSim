---
title: Your own models
description: Write a simulation folder from your FMUs with one command.
---

# Your own models

`ecosim new` writes a simulation folder from FMU files: a folder for each model with the FMU, its `.fmc` file and its
client config, and `server/` with the server config and `simulation.json`. It connects the inputs and outputs that
have the same name, `--connect` connects others, and at the end it checks the simulation as `ecosim check` does. The
files are the ones you would write by hand, so you can change them later.

The commands below run in `simulation_examples`, where `uv run` finds the `ecosim` command. The three FMUs of the
building example make the same simulation as the hand-written files:

```shell
uv run ecosim new my_building building/Modules/house/house.fmu building/Modules/occupancy/occupancy.fmu \
    building/Modules/weather/weather.fmu --steps 100 --start-date 2023-01-01
```

```text
Wrote my_building: 3 simulators, 18 connections, no problems.
100 steps of 15 min, from 2023-01-01 00:00 to 2023-01-02 01:00 UTC.
The step size 15min is the default. Choose another with --step-size.
  house      FMI 2.0  my_building/Modules/house      18 inputs   6 outputs
  occupancy  FMI 2.0  my_building/Modules/occupancy   0 inputs   7 outputs
  weather    FMI 2.0  my_building/Modules/weather     0 inputs  24 outputs
Connections:
  house <- weather, 11 connections
    weatherBus_TDryBul  <-  weatherBus.TDryBul
    weatherBus_HDifHor  <-  weatherBus.HDifHor
    ...
  house <- occupancy, 7 connections
    occupancyBus_Qdot_sen_human   <-  occupancyBus.Qdot_sen_human
    ...
After a change, check it with: uv run ecosim check my_building
Run it with: uv run ecosim run my_building
```

```shell
uv run ecosim run my_building
```

These are the 18 connections of `building/server/simulation.json`, and the run gives the same results as the
hand-written simulation. The weather model stores 24 values a step instead of 11, since `ecosim new` keeps every output.
A command that `ecosim` prints for you to copy starts the way you started `ecosim`, with `uv run` in
`simulation_examples`.

If the check at the end finds a problem, like an FMU without a binary for this computer, the output lists it under
`Problems:` and `ecosim new` ends with exit code 1. The simulation stays written, so you can fix its files and check it
again.

## The models

- An FMU argument is an `.fmu` file, a folder, or `NAME=FILE`. A folder adds every `.fmu` file directly in it, in
  the order of their names, and not those in its folders. On Windows, where `*.fmu` is not expanded, a folder is
  the way to give many FMUs at once.
- A model is named after its file, without `.fmu` and with `_` for every character other than letters, digits, `_`
  and `-`. `NAME=FILE` gives it another name, for example `house2=house.fmu` for a second house. The name is also
  the name of its simulator and of its folder in `Modules/`. Two names that differ only in case are refused.
- The models keep the order of the arguments, which is the order of `simulators` in `simulation.json`.
- `ecosim new` takes FMI 2.0 and FMI 3.0 FMUs for co-simulation. A Python, MATLAB or Pyro5 model is added by hand,
  see the [Python client](../guides/python-client.md) guide.

## How the inputs get connected

An input is connected to an output of another model if that output is the only one with the same name. A dot and an
underscore count as the same, so `weatherBus_TDryBul` gets its value from `weatherBus.TDryBul`. An FMI 3.0 array is
only connected to an input that takes as many values. A connection between two units, like `degC` and `K`, is marked
in the list. Nothing converts the values.

Every other input keeps the start value of its FMU. It is listed with the reason, and with the closest name of an
output if one is very close. Four FMUs whose names do not all match, a house with a heating and a ventilation that
control its room temperature. They are FMUs of the tests in
`ecosim-test-common/ecosim_test_common/resources/fmu_v2/models/house/`, in `linux` or `windows`, and the commands
below leave out that folder:

```shell
uv run ecosim new house_simulation weather.fmu house.fmu heating.fmu ventilation.fmu --step-size 1min --steps 200
```

```text
Wrote house_simulation: 4 simulators, 2 connections, no problems.
200 steps of 1 min, from 2024-01-01 00:00 to 2024-01-01 03:20 UTC.
The start date 2024-01-01 is the default. Choose another with --start-date.
  weather      FMI 2.0  house_simulation/Modules/weather      0 inputs  26 outputs
  house        FMI 2.0  house_simulation/Modules/house        2 inputs    1 output
  heating      FMI 2.0  house_simulation/Modules/heating      0 inputs    1 output
  ventilation  FMI 2.0  house_simulation/Modules/ventilation  0 inputs   2 outputs
Connections:
  house <- weather, 1 connection
    T_out  <-  T_out
  house <- ventilation, 1 connection
    ventilation_pressure_control_signal  <-  ventilation_pressure_control_signal
Not connected, so these inputs keep the start value of their FMU:
  house.dir_sol_iradiance: no output of another model has this name. Did you mean weather.dir_sol_irradiance? Then add --connect house.dir_sol_iradiance=weather.dir_sol_irradiance
  house.heating_heatExchanger_control_signal: no output of another model has this name.
  house.vetnilation_valve_control_signal: no output of another model has this name. Did you mean ventilation.ventilation_valve_control_signal? Then add --connect house.vetnilation_valve_control_signal=ventilation.ventilation_valve_control_signal
  heating.T_room: no output of another model has this name.
  ventilation.T_room: no output of another model has this name.
After a change, check it with: uv run ecosim check house_simulation
Run it with: uv run ecosim run house_simulation
```

The table counts the inputs that `simulation.json` connects, as `ecosim check` does. An input that is not connected
is in the `.fmc` file, but not in `simulation.json`. To connect it in an existing simulation, add it to its simulator in
`simulation.json` with `connected_to`, see [Configuration files](../reference/configuration-files.md#simulation-config).

## Other names and loops

`--connect INPUT=OUTPUT` connects an input to an output of another name, like
`--connect heating.T_room=house.room_temperature`. It replaces the match by name. Give it once for each input.

The house and its two controllers then feed each other: the house needs the signals of the controllers, and the
controllers need the room temperature of the house. The server starts a model in a step only when all its inputs
have a value, so it could start none of them. `ecosim new` finds such a loop and stops before it writes anything:

```shell
uv run ecosim new house_simulation weather.fmu house.fmu heating.fmu ventilation.fmu --step-size 1min --steps 200 \
    --connect house.dir_sol_iradiance=weather.dir_sol_irradiance \
    --connect house.heating_heatExchanger_control_signal=heating.heating_control_signal \
    --connect house.vetnilation_valve_control_signal=ventilation.ventilation_valve_control_signal \
    --connect heating.T_room=house.room_temperature --connect ventilation.T_room=house.room_temperature
```

```text
ecosim new: error: heating, house and ventilation feed each other, so the server could start none of them:
  house.ventilation_pressure_control_signal  <-  ventilation.ventilation_pressure_control_signal
  house.heating_heatExchanger_control_signal  <-  heating.heating_control_signal
  house.vetnilation_valve_control_signal  <-  ventilation.ventilation_valve_control_signal
  heating.T_room  <-  house.room_temperature
  ventilation.T_room  <-  house.room_temperature
Give inputs the value of the step before to break the loop, for example:
  --logical-delay heating.T_room --logical-delay ventilation.T_room
(run with --debug for the full traceback)
```

`--logical-delay INPUT` gives a connected input the value of the step before, which breaks the loop. In the first
step the input gets the start value of the FMU, or the one after `=`, like `--logical-delay heating.T_room=293.15`.
An FMI 3.0 array takes one number for each value, like `=1,2,3`. With the two delays the simulation is written, and the
list shows each delayed input with its start value:

```text
  heating <- house, 1 connection
    T_room  <-  room_temperature   (given with --connect, one step later, starts at 293.15)
  ventilation <- house, 1 connection
    T_room  <-  room_temperature   (given with --connect, one step later, starts at 293.15)
```

Check the start value. The controllers of this example start at 0 K in their FMUs, so without `=293.15` their
first steps differ. An input connected to an output of its own model always needs a logical delay.

## What goes into the files

- The `.fmc` file lists every input and output the FMU client can exchange, Real variables of FMI 2.0 and Float64
  variables of FMI 3.0, with the unit and the description from the FMU. The variables of other types are listed
  under `Left out of the .fmc files`.
- `simulation.json` has every output of every model, so a run stores all of them. Leave out the ones you do not
  need, and the result files get smaller.
- The time goes into `setup`: `--step-size` as `delta_t`, `--duration` or `--steps` as `steps`, and `--start-date`
  as `start_date`. A duration has a unit: `ms`, `s`, `min`, `h`, `d` or `y`, where `1y` is 365 days. A step size
  without a unit is in milliseconds. Without the options, a simulation has steps of 15 minutes for one day from
  2024-01-01, and the output says which values are such defaults. A date without an offset is UTC.
- `--database-type postgres` writes a `[database]` section for PostgreSQL. Fill in the server and the user, and
  give the password with `PGPASSWORD` or a password file. Without it the results are written as files.
- `--port` sets the port of the server in the server config and in every client config. `ecosim run` does not need
  it, since it picks a free port.

| In the simulation folder | Content |
| --- | --- |
| `Modules/<model>/<model>.fmu` | a copy of the FMU |
| `Modules/<model>/<model>.fmc` | the inputs and outputs of the model |
| `Modules/<model>/preferences.ini` | the client config: the server, the simulator and the FMU |
| `server/simulation.json` | the simulators, their connections and the setup |
| `server/preferences.ini` | the server config |

The target folder must not exist yet, or be empty. The files are written into a draft folder first and moved into
place at the end, so a stop in between leaves no half-written simulation.

## Change and run it

The result is a normal simulation folder. Change a file, then check it again with `ecosim check my_building`.
`ecosim run my_building` runs it with the length of its setup, and `--steps` or `--duration` of `ecosim run`
override it. A parameter of an FMU goes into `[start_values]` of its client config, see
[Configuration files](../reference/configuration-files.md#start-values). To start the server and the clients by
hand, for example on several machines, see [Run a simulation](../guides/run-a-simulation.md#start-the-parts-by-hand). For a
simulation that `ecosim new` wrote, start them in its folder, with `server/preferences.ini`, `server/simulation.json` and
`Modules/<model>/preferences.ini` as their config files. The server then writes the results to `results/by_hand`,
apart from the run folders of `ecosim run`.
