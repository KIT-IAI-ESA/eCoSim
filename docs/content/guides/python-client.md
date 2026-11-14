---
title: Python client
description: Couple a Python model that runs in the process of the client.
---

# Python client

`ecosim-client-python` couples a Python model, for example a pandapower grid or a controller. The model
runs in the process of the client, so there is no Pyro5 daemon to start and no port to choose.

## The model

The model is a class with three methods, the same ones a [Pyro5 object](pyro5-client.md#the-pyro-object) has:

| Method | Called |
| --- | --- |
| `initialize()` | once, before the first step. It returns a dictionary with every output. |
| `do_step(value_dict)` | every step. `value_dict` holds the inputs from the other simulators. It returns a dictionary with every output. |
| `clear()` | once, at the end. It is not called if the simulation never started. |

`do_step` also gets the time and the step size if it has parameters with these names:

- `current_simulation_time`: the seconds since the start of the simulation, at the start of this step. The
  first step starts at 0.
- `step_size_in_seconds`: the length of this step in seconds.

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

Outputs are numbers. `int`, `bool` and numpy numbers become `float`, also in a list. An array output is a list
of numbers, so a numpy array has to become a list first, with `tolist()`.
The client stops with a message that names the model and the output if an output is missing, `None` or not a
number, or if `initialize()` or `do_step()` returns something other than a dictionary.

## Configuration

Save the class as `room.py` next to the client's `preferences.ini`, and name it in the `[python]` section:

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

`model` names the module, without `.py`, and the class, with a `:` between them. The client looks for the
module in the folder of the ini file first and then in the installed packages, so `model = mypackage.grid:Grid`
works too. The client creates the model without arguments, as `Room()`. A function that returns the model can
take the place of the class.

The client imports the module, so the code at its top level runs when the client starts. Keep the class
and what it needs there, and nothing that waits, such as a Pyro5 daemon.

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

The model runs in the Python environment of the client, so the packages it imports have to be installed
there. Add them to the project, for example with `uv add --project ../.. pandapower`. To add a package for
one run only, use `uv run --with` and start the client with `python -m`. The `ecosim-client-python` command
runs in the environment of the project and does not see a package that `--with` adds:

```shell
uv run --project ../.. --with pandapower python -m ecosim_client_python.main --config-file ../Modules/grid/preferences.ini
```

The client checks the model before it connects to the server. A missing module, class or method, or a
package that the model imports and that is not installed, stops it within a second:

```text
ecosim-client-python: error: /home/user/simulation/Executable/../Modules/room/room.py has no Rom. Did you mean Room? (run with --debug for the full traceback)
```

An error in the code of the model while the client imports or creates it also ends in one line, and that line
names the model. Run the client with `--debug` to see the line of the model code that failed.
`initialize()` runs later, when the simulation starts. An error there stops the client too, and its log
names the model and shows the line of the model code that failed.

## Move a model from the Pyro5 client

A Pyro5 object runs in this client as it is. `import Pyro5.api` and `@Pyro5.api.expose` can stay if Pyro5
is installed in the environment of the client, otherwise delete both. Move the lines that start the daemon
under `if __name__ == "__main__":`, or delete them, because the client would wait in `requestLoop()` when it
imports the module. In `preferences.ini`, replace the `[pyro]` section with a `[python]` section with
`model = <module>:<class>`, and set `type = python`. Then start `ecosim-client-python` in place of the daemon
and `ecosim-client-pyro5`.

A model that counts its own steps can use `current_simulation_time` instead.

Keep the Pyro5 client for a model that needs another Python environment or another machine.
