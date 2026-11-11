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
