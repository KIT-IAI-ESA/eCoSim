---
title: Your own models
description: Write a simulation folder from your FMUs with one command.
---

# Your own models

`ecosim new` writes a simulation folder from FMU files. Each model gets a folder with the FMU, its `.fmc` file and
its client config. `server/` gets the server config and `simulation.json`. Inputs and outputs with the same name
are connected. You can change all these files later.

The commands below run in `simulation_examples`. The three FMUs of the building example give the same simulation
as the files of the example:

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

These are the 18 connections of `building/server/simulation.json`. The run gives the same results as the building
example. The weather model stores 24 values per step instead of 11. `ecosim new` keeps every output.

At the end `ecosim new` checks the simulation like `ecosim check`. A problem is listed under `Problems:` and the
exit code is 1. The files are written anyway. Fix them and check again.

## The models

An FMU argument is an `.fmu` file, a folder with `.fmu` files or `NAME=FILE`. A model is named after its file.
`NAME=FILE` sets another name, for example `house2=house.fmu` for a second house. The name is also the name of
the simulator and of its folder in `Modules/`.

`ecosim new` takes FMI 2.0 and FMI 3.0 FMUs for co-simulation. Add a Python, MATLAB or Pyro5 model manually, see
the [Python client](../guides/python-client.md) guide.

## How the inputs get connected

An input is connected to the output of another model with the same name. A dot and an underscore count as the
same: `weatherBus_TDryBul` gets its value from `weatherBus.TDryBul`. Values are not converted between units. A
connection between two different units, like `degC` and `K`, is marked in the list.

Every other input keeps the start value of its FMU. The output lists it, with the closest output name if there is
one. The next example has four FMUs whose names do not all match: a house with a heating and a ventilation that
control its room temperature. The FMUs are test files in
`ecosim-test-common/ecosim_test_common/resources/fmu_v2/models/house/`, in `linux` or `windows`. The commands
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
Not connected. These inputs keep the start value of their FMU:
  house.dir_sol_iradiance: no output of another model has this name. Did you mean weather.dir_sol_irradiance? Then add --connect house.dir_sol_iradiance=weather.dir_sol_irradiance
  house.heating_heatExchanger_control_signal: no output of another model has this name.
  house.vetnilation_valve_control_signal: no output of another model has this name. Did you mean ventilation.ventilation_valve_control_signal? Then add --connect house.vetnilation_valve_control_signal=ventilation.ventilation_valve_control_signal
  heating.T_room: no output of another model has this name.
  ventilation.T_room: no output of another model has this name.
After a change, check it with: uv run ecosim check house_simulation
Run it with: uv run ecosim run house_simulation
```

The table counts only the connected inputs. An input that is not connected is in the `.fmc` file but not in
`simulation.json`. To connect it later, add it to its simulator in `simulation.json` with `connected_to`, see
[Configuration files](../reference/configuration-files.md#simulation-config).

## Other names and loops

`--connect INPUT=OUTPUT` connects an input to an output with another name, like
`--connect heating.T_room=house.room_temperature`. Pass it once per input.

With all five connections the house and its two controllers form a loop. The house needs the signals of the
controllers and the controllers need the room temperature of the house. `ecosim new` finds the loop and writes
nothing. Delete the `house_simulation` folder of the first command before you run this one:

```shell
uv run ecosim new house_simulation weather.fmu house.fmu heating.fmu ventilation.fmu --step-size 1min --steps 200 \
    --connect house.dir_sol_iradiance=weather.dir_sol_irradiance \
    --connect house.heating_heatExchanger_control_signal=heating.heating_control_signal \
    --connect house.vetnilation_valve_control_signal=ventilation.ventilation_valve_control_signal \
    --connect heating.T_room=house.room_temperature --connect ventilation.T_room=house.room_temperature
```

```text
ecosim new: error: heating, house and ventilation form a loop:
  house.ventilation_pressure_control_signal  <-  ventilation.ventilation_pressure_control_signal
  house.heating_heatExchanger_control_signal  <-  heating.heating_control_signal
  house.vetnilation_valve_control_signal  <-  ventilation.ventilation_valve_control_signal
  heating.T_room  <-  house.room_temperature
  ventilation.T_room  <-  house.room_temperature
Break the loop with a logical delay, for example:
  --logical-delay heating.T_room --logical-delay ventilation.T_room
(run with --debug for the full traceback)
```

`--logical-delay INPUT` gives a connected input the value of the previous step. That breaks the loop. In the first
step the input gets the start value of the FMU or the value after `=`, like `--logical-delay heating.T_room=293.15`.
With the two delays the simulation is written. The list shows each delayed input with its start value:

```text
  heating <- house, 1 connection
    T_room  <-  room_temperature   (given with --connect, one step later, starts at 293.15)
  ventilation <- house, 1 connection
    T_room  <-  room_temperature   (given with --connect, one step later, starts at 293.15)
```

Check the start value. The controllers of this example start at 0 K in their FMUs. An input connected to an output
of its own model always needs a logical delay.

## What goes into the files

| In the simulation folder | Content |
| --- | --- |
| `Modules/<model>/<model>.fmu` | a copy of the FMU |
| `Modules/<model>/<model>.fmc` | the inputs and outputs of the model. Only Real variables of FMI 2.0 and Float64 variables of FMI 3.0 |
| `Modules/<model>/preferences.ini` | the client config: the server, the simulator and the FMU |
| `server/simulation.json` | the simulators with all their outputs, the connections and the setup |
| `server/preferences.ini` | the server config. With `--database-type postgres` fill in the server and the user in `[database]` |

`--step-size`, `--duration` or `--steps` and `--start-date` set the time in the setup of `simulation.json`. Without
them a simulation has steps of 15 minutes for one day from 2024-01-01. The output shows which values are defaults.

`simulation.json` has every output of every model. Remove the outputs you do not need to get smaller result files.

The target folder must be empty or not exist yet.

## Change and run it

The result is a normal simulation folder. After a change, check it again with `ecosim check my_building`.
`ecosim run my_building` runs it with the length of its setup. `--steps` or `--duration` of `ecosim run` override
it. A parameter of an FMU goes into `[start_values]` of its client config, see
[Configuration files](../reference/configuration-files.md#start-values).

To start the server and the clients manually, for example on several machines, see
[Run a simulation](../guides/run-a-simulation.md#start-the-server-and-the-clients-manually). Start them in the
simulation folder. The server then writes the results to `results/manual`.
