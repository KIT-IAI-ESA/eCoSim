# eCoSim

A co-simulation framework for energy systems.

[![tests](https://github.com/KIT-IAI-ESA/eCoSim/actions/workflows/tests.yml/badge.svg)](https://github.com/KIT-IAI-ESA/eCoSim/actions/workflows/tests.yml)
[![docs](https://github.com/KIT-IAI-ESA/eCoSim/actions/workflows/docs.yml/badge.svg)](https://ecosim.easimov.com/docs)

eCoSim couples independent simulation models, such as a house, its heating and the weather, into one
co-simulation. A server owns the clock and the data flow. Each model runs in its own client, and for
every step the server sends each client its inputs, receives its outputs and passes them on to the
inputs they are connected to.

Clients exist for FMI 2.0 and FMI 3.0 models, for MATLAB scripts and for Python models served over
Pyro5. The server stores the results in PostgreSQL/TimescaleDB or as JSON lines on disk. For many
simulations at once, `ecosim-hpc` runs the server and the clients on a Dask cluster.

## Packages

| Folder | Purpose |
| --- | --- |
| `ecosim-server` | The server: runs the simulation and stores the results |
| `ecosim-client-fmu-v2` | Client for FMI 2.0 models |
| `ecosim-client-fmu-v3` | Client for FMI 3.0 models |
| `ecosim-client-matlab` | Client for models written as MATLAB scripts |
| `ecosim-client-pyro5` | Client for Python models served over Pyro5 |
| `ecosim-hpc` | Runs the server and the clients on a Dask cluster |
| `ecosim-common`, `ecosim-common-fmpy` | Code shared by the packages |
| `ecosim-test-common` | Shared test helpers, test data and models |
| `integration-tests` | Tests that run the packages together |

`simulation_examples/` holds the examples, `docs/` the documentation and `dev/` the scripts for
development.

## Installation

eCoSim is installed from source. You need Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
The MATLAB client needs exactly Python 3.12.

```shell
git clone https://github.com/KIT-IAI-ESA/ecosim.git
cd ecosim
```

Each package is its own uv project. `uv run --project <folder>` creates the environment of that
folder the first time it is used, so there is no separate install step. See
[Installation](https://ecosim.easimov.com/docs/getting-started/installation) for the details.

## Quick start

The building example couples three FMI 2.0 models for 100 steps and writes the results as files, so
no database is needed. Start the server:

```shell
cd simulation_examples/building/Executable
uv run --project ../.. ecosim-server --server-config ../server/preferences.ini \
    --simulation-config ../server/simulation.json --steps 100 \
    --database-type file --database-directory results
```

The first run creates the environment, which takes a moment. The server then waits for the
clients. In a second terminal, in the same folder, start them:

```shell
for module in house occupancy weather; do
    uv run --project ../.. ecosim-client-fmu-v2 --config-file "../Modules/$module/preferences.ini" &
done
wait
```

When the simulation is finished, the server and the clients exit, and `results/` holds the outputs
of each model as JSON lines. The [quick start](https://ecosim.easimov.com/docs/getting-started/quick-start)
explains the results and the files of the example.

## Documentation

The documentation is at [ecosim.easimov.com/docs](https://ecosim.easimov.com/docs).

- Guides: [Docker](https://ecosim.easimov.com/docs/guides/docker),
  [HPC cluster](https://ecosim.easimov.com/docs/guides/hpc-cluster),
  [MATLAB client](https://ecosim.easimov.com/docs/guides/matlab-client),
  [Pyro5 client](https://ecosim.easimov.com/docs/guides/pyro5-client)
- Reference: [command line](https://ecosim.easimov.com/docs/reference/command-line),
  [configuration files](https://ecosim.easimov.com/docs/reference/configuration-files)

## Development

Questions, bug reports and pull requests are welcome, see [Contributing](CONTRIBUTING.md). To work on
eCoSim itself, start with the project setup.

- [Project setup](docs/content/development/project-setup.md)
- [Architecture](docs/content/development/architecture.md)
- [Developing](docs/content/development/developing.md)
- [Testing](docs/content/development/testing.md)
- [Dependencies](docs/content/development/dependencies.md)
- [Adding a subproject](docs/content/development/adding-a-subproject.md)
- [Coding guidelines](docs/content/development/coding-guidelines.md)
- [Development tips](docs/content/development/tips.md)
- [Release history](docs/content/development/release-history.md)

## Credits

eCoSim is a project of the [Energy System Analysis](https://www.iai.kit.edu/english/groups_4104.php)
research group at the [Institute for Automation and Applied Informatics (IAI)](https://www.iai.kit.edu/english/index.php)
of the [Karlsruhe Institute of Technology (KIT)](https://www.kit.edu/english/index.php). See also
[eASiMOV](https://easimov.cloud.iai.kit.edu) and the [Energy Lab](https://www.elab.kit.edu/english/index.php).

## Citing eCoSim

If you use eCoSim in your work, please cite it. The details are in [CITATION.cff](CITATION.cff), and
GitHub shows them under "Cite this repository" on the repository page.

## Licence

eCoSim is released under the [Apache License 2.0](LICENSE).
