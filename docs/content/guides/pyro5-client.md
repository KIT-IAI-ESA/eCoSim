---
title: Pyro5 client
description: Couple a Python model that runs in its own process.
---

# Pyro5 client

`ecosim-client-pyro5` couples a Python model that runs in its own process and is published as a
[Pyro5](https://pyro5.readthedocs.io/) object, for example a pandapower grid.

## Configuration

The `[pyro]` section of the client's `preferences.ini` tells the client where to find the object:

| Key | Meaning |
| --- | --- |
| `pyro_host` | Host name or IP address of the machine where the Python process with the Pyro object runs |
| `pyro_port` | The port Pyro uses. Choose a different port than the one of the server and the database. |
| `pyro_object_name` | The name of the published Pyro object, the `objectId` passed to `daemon.register()` |

:::note

The section name is `pyro`, in lowercase. Section names in the ini files are case-sensitive.

:::

The other keys are the same as for every client, see the [configuration reference](../reference/configuration-files.md).

## The Pyro object

The object provides three methods, which the client calls:

| Method | Called |
| --- | --- |
| `initialize()` | once, before the simulation starts. The method must return a dictionary with every output. |
| `do_step(value_dict)` | every step. `value_dict` holds the inputs from the other simulators. The method must return a dictionary with every output. |
| `clear()` | once, after the simulation ends |

The model gets neither the simulation time nor the step size, so it has to keep its own clock and know the step size.

A small Pyro object, with an input `heating_power` and an output `temperature` in the client's `.fmc` file:

```python
import Pyro5.api


@Pyro5.api.expose
class Room:
    def __init__(self) -> None:
        self.temperature = 20.0
        self.running = True

    def initialize(self) -> dict[str, float]:
        return {"temperature": self.temperature}

    def do_step(self, value_dict: dict[str, float]) -> dict[str, float]:
        self.temperature += 0.001 * value_dict["heating_power"]
        return {"temperature": self.temperature}

    def clear(self) -> None:
        self.running = False


room = Room()
daemon = Pyro5.api.Daemon(host="localhost", port=51234)
daemon.register(room, objectId="room")
daemon.requestLoop(loopCondition=lambda: room.running)
daemon.close()
```

Start the script before the client. Here `pyro_host` is `localhost`, `pyro_port` is `51234` and
`pyro_object_name` is `room`. To reach it from another machine, use that machine's host name or IP address
instead of `localhost`.

The script ends after the client has called `clear()`. `clear()` only sets `running`, because a daemon that
is shut down inside a call closes the connection before the client gets the answer, and the client then
fails with `ConnectionClosedError`.

## Reach the Pyro object

eCoSim does not start the Python process with the Pyro object, it only connects to it. Whoever sets up the run
makes sure the client reaches the object:

- the process runs and the object is registered under `pyro_object_name` before the simulation starts; the client
  connects when it calls `initialize()`
- the daemon listens on an address the client can reach. A `Pyro5.api.Daemon()` without a host listens on
  `localhost` only, so a client on another machine needs the host set explicitly:

  ```python
  daemon = Pyro5.api.Daemon(host="<host name or IP address>", port=<pyro_port>)
  daemon.register(model, objectId="<pyro_object_name>")
  daemon.requestLoop()
  ```

- `pyro_host` and `pyro_port` in `preferences.ini` are the same host and port, and no firewall blocks the port
- several Pyro objects on one host use different ports

`localhost` as `pyro_host` only works if the client runs on the same machine as the Pyro object. On an HPC
cluster that is most likely not the case, see [HPC cluster](hpc-cluster.md#pyro5-simulators).
