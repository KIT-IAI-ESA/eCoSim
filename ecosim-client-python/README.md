# eCoSim client for Python models

`ecosim-client-python` couples a Python model with an eCoSim server. The model runs in the process of
the client. No Pyro5 daemon is needed.

The model is a class with three methods:

- `initialize()` returns a dictionary with every output
- `do_step(value_dict)` gets the inputs and returns a dictionary with every output
- `clear()` runs once at the end

The `[python]` section of the client's `preferences.ini` sets the module and the class:

```ini
[python]
model = room:Room
```

`room.py` can be in the folder of the ini file.

```shell
ecosim-client-python --config-file Modules/room/preferences.ini
```

See the [Python client guide](https://ecosim.easimov.com/docs/guides/python-client) for the details.
