# eCoSim client for Python models

`ecosim-client-python` couples a Python model with an eCoSim server. The model runs in the process of
the client, so there is no Pyro5 daemon to start and no port to choose.

The model is a class with three methods:

- `initialize()` returns a dictionary with every output
- `do_step(value_dict)` gets the inputs and returns a dictionary with every output. It also gets
  `current_simulation_time` and `step_size_in_seconds` if it has parameters with these names.
- `clear()` runs once at the end

The `[python]` section of the client's `preferences.ini` names the module and the class:

```ini
[python]
model = room:Room
```

The folder of the ini file is searched first, so `room.py` can sit next to it.

```shell
ecosim-client-python --config-file Modules/room/preferences.ini
```

See the [Python client guide](https://ecosim.easimov.com/docs/guides/python-client) for the details.
