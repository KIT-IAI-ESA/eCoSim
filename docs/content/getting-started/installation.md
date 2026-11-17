---
title: Installation
description: Requirements, and how to get eCoSim from source.
---

# Installation

## Requirements

- Linux or Windows. macOS is not tested.
- Python 3.12 or newer. The MATLAB client needs exactly Python 3.12.
- [uv](https://docs.astral.sh/uv/), which creates the environments and installs the dependencies
- PostgreSQL/TimescaleDB, only if the results should go into a database
- Docker, only for the [Docker guide](../guides/docker.md)

## Get the source

```shell
git clone https://github.com/KIT-IAI-ESA/ecosim.git
cd ecosim
```

eCoSim is installed from source. The repository holds one uv project per package, and
`uv run --project <folder>` creates the environment of that folder the first time it is used, so
there is no separate install step. The [quick start](quick-start.md) works this way in
`simulation_examples`.

To set up all packages at once, run `python dev/init_dev.py` in the repository root. It creates the
environment of every package with its development tools and installs the pre-commit hooks, see
[Project setup](../development/project-setup.md).

## Packages

| Package | Command | Purpose |
| --- | --- | --- |
| `ecosim` | `ecosim` | Runs a simulation locally with `ecosim new`, `ecosim check`, `ecosim run` and `ecosim results`. Installs the server, both FMU clients and the Python client |
| `ecosim-server` | `ecosim-server` | The simulation server: state, repositories, measurements |
| `ecosim-client-fmu-v2` | `ecosim-client-fmu-v2` | Client for FMI 2.0 models |
| `ecosim-client-fmu-v3` | `ecosim-client-fmu-v3` | Client for FMI 3.0 models |
| `ecosim-client-matlab` | `ecosim-client-matlab` | Client for MATLAB models, see the [MATLAB client](../guides/matlab-client.md) |
| `ecosim-client-pyro5` | `ecosim-client-pyro5` | Client for Python models served over Pyro5, see the [Pyro5 client](../guides/pyro5-client.md) |
| `ecosim-client-python` | `ecosim-client-python` | Client for Python models that run in the process of the client, see the [Python client](../guides/python-client.md) |
| `ecosim-hpc` | `ecosim-hpc`, started with `mpirun` | Runs server and clients on a Dask cluster, see the [HPC cluster](../guides/hpc-cluster.md) |
| `ecosim-common`, `ecosim-common-fmpy` | | Shared code |

Every command lists its options with `--help` and prints its version with `--version`. The
[command-line reference](../reference/command-line.md) has the same lists.

Start with `ecosim`. A local run needs nothing else. Its extras add the Pyro5 client, `ecosim[pyro5]`, and pandas
for the results, `ecosim[pandas]`. The MATLAB client needs Python 3.12 and its own environment, see the
[MATLAB client](../guides/matlab-client.md).

`simulation_examples/` is a uv project that installs `ecosim`, the server, the clients and `ecosim-hpc` together.
The examples use it. To have the `ecosim` command in every folder, install it from the clone as a uv tool:

```shell
uv tool install --editable ./ecosim
```

To work on eCoSim itself, see [Project setup](../development/project-setup.md).

## Network

The server and the clients talk without a login and without encryption, so anyone who can reach the
server port can join a run. By default the server only listens on `localhost`. When you set another
host, run eCoSim only in a network you trust, for example inside a cluster job or behind a firewall.
The [security policy](https://github.com/KIT-IAI-ESA/eCoSim/blob/main/SECURITY.md) says how to report
a security problem.
