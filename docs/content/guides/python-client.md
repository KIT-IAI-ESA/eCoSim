---
title: Python client
description: Couple a Python model that runs in the process of the client.
---

# Python client

`ecosim-client-python` couples a Python model, for example a pandapower grid or a controller. The model
runs in the process of the client. No Pyro5 daemon is needed.

## The model

The model is a class with three methods, the same as a [Pyro5 object](pyro5-client.md#the-pyro-object):

| Method | Called |
| --- | --- |
| `initialize()` | once, before the first step. It returns a dictionary with every output. |
| `do_step(value_dict)` | every step. `value_dict` has the inputs from the other simulators. It returns a dictionary with every output. |
| `clear()` | once, at the end |

`do_step` also gets the time and the step size if it has parameters with these names:

- `current_simulation_time`: the seconds since the start of the simulation, at the start of this step
- `step_size_in_seconds`: the length of this step in seconds

A room that is heated in the morning and in the evening, with an input `outdoor_temperature` and an output
`temperature`:

```python
class Room:
    def __init__(self) -> None:
        self.temperature = 293.15

    def initialize(self) -> dict[str, float]:
        return {"temperature": self.temperature}

    def do_step(self, value_dict: dict[str, float], current_simulation_time: float, step_size_in_seconds: float) -> dict[str, float]:
        hour = current_simulation_time / 3600 % 24
        heating_power = 2000.0 if 6 <= hour < 9 or 17 <= hour < 22 else 0.0
        heat_loss = 50.0 * (self.temperature - value_dict["outdoor_temperature"])
        self.temperature += (heating_power - heat_loss) * step_size_in_seconds / 1.0e6
        return {"temperature": self.temperature}

    def clear(self) -> None:
        pass
```

An output is a number or a list of numbers. Convert a numpy array with `tolist()` first.

## Configuration

Save the class as `room.py` next to the client's `preferences.ini` and set it in the `[python]` section:

```ini
[server]
ip = localhost
port = 1234

[simulator]
simulator_name = room
model_name = room
type = python
fmc_file = [room.fmc]

[python]
model = room:Room
```

`model` is the module without `.py`, a `:` and the class. The client looks for the module in the folder of the
ini file first, then in the installed packages. `model = mypackage.grid:Grid` works too. The client creates
the model without arguments, as `Room()`.

The client imports the module. The code at its top level runs when the client starts. Do not start anything
there that waits, such as a Pyro5 daemon.

As for every client, the `.fmc` file lists the inputs and outputs:

```json
{"inputs": [{"name": "outdoor_temperature", "unit": "K", "required": "true"}], "outputs": [{"name": "temperature", "unit": "K"}]}
```

The other keys are the same as for every client, see the [configuration reference](../reference/configuration-files.md).

## Run it

In the `Executable` folder of an example:

```shell
uv run --project ../.. ecosim-client-python --config-file ../Modules/room/preferences.ini
```

The model runs in the Python environment of the client. The packages it imports have to be installed there,
for example with `uv add --project ../.. pandapower`. To add a package for one run only, use `uv run --with`
and start the client with `python -m`. The `ecosim-client-python` command does not see a package that `--with`
adds:

```shell
uv run --project ../.. --with pandapower python -m ecosim_client_python.main --config-file ../Modules/grid/preferences.ini
```

The client checks the model before it connects to the server. A missing module, class, method or package
stops it right away:

```text
ecosim-client-python: error: /home/user/simulation/Executable/../Modules/room/room.py has no Rom. Did you mean Room? (run with --debug for the full traceback)
```

`initialize()` runs later, when the simulation starts. An error there stops the client too, and its log
names the model and shows the line of the model code that failed.

## Move a model from the Pyro5 client

A Pyro5 object runs in this client as it is. `import Pyro5.api` and `@Pyro5.api.expose` can stay if Pyro5
is installed in the environment of the client. Otherwise delete both. Move the lines that start the daemon
under `if __name__ == "__main__":` or delete them. The client would wait in `requestLoop()` when it imports
the module. In `preferences.ini`, replace the `[pyro]` section with a `[python]` section with
`model = <module>:<class>` and set `type = python`. Then start `ecosim-client-python` in place of the daemon
and `ecosim-client-pyro5`.

Keep the Pyro5 client for a model that needs another Python environment or another machine.
