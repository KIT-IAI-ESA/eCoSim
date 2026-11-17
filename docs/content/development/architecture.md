# Architecture

## Subprojects

Twelve independent uv projects. Each has its own `pyproject.toml`, `uv.lock` and `.venv`, and
`dev/config.py:SUBPROJECTS` is the list the tooling iterates over.

| Subproject | Import package | Purpose |
| --- | --- | --- |
| `ecosim` | `ecosim` | The `ecosim` command to write, check and run a simulation locally and to read its results |
| `ecosim-common` | `ecosim_common` | Shared abstractions: config, communication, simulation primitives |
| `ecosim-common-fmpy` | `ecosim_common_fmpy` | Shared FMU/fmpy code for the FMU clients and `ecosim-hpc` |
| `ecosim-server` | `ecosim_server` | The simulation server: state, repositories, measurements |
| `ecosim-client-fmu-v2` | `ecosim_client_fmu_v2` | Client for FMI 2.0 models |
| `ecosim-client-fmu-v3` | `ecosim_client_fmu_v3` | Client for FMI 3.0 models |
| `ecosim-client-matlab` | `ecosim_client_matlab` | Client for Matlab models |
| `ecosim-client-pyro5` | `ecosim_client_pyro5` | Client bridging via Pyro5 (e.g. pandapower) |
| `ecosim-client-python` | `ecosim_client_python` | Client for Python models that run in the process of the client |
| `ecosim-hpc` | `ecosim_hpc` | HPC entry point and client manager |
| `ecosim-test-common` | `ecosim_test_common` | Shared fixtures, test data and FMU resources |
| `integration-tests` | `integration_tests` | Cross-package tests, needs the others installed |

## Dependency direction

An arrow points from a subproject to one it depends on. Every subproject also depends on
`ecosim-common`, which is left out of the diagram.

```mermaid
flowchart TD
  tests[integration-tests] --> hpc[ecosim-hpc]
  tests --> testcommon[ecosim-test-common]
  tests --> python[ecosim-client-python]
  ecosim[ecosim] --> server
  ecosim --> fmu2
  ecosim --> fmu3
  ecosim --> python
  ecosim --> fmpy
  hpc --> server[ecosim-server]
  hpc --> fmu2[ecosim-client-fmu-v2]
  hpc --> fmu3[ecosim-client-fmu-v3]
  hpc --> matlab[ecosim-client-matlab]
  hpc --> pyro[ecosim-client-pyro5]
  hpc --> python
  hpc --> fmpy[ecosim-common-fmpy]
  fmu2 --> fmpy
  fmu3 --> fmpy
```

- `ecosim-common` depends on no other subproject; everything else depends on it
- the two FMU clients use `ecosim-common-fmpy`, and `ecosim-hpc` chooses the client of each simulator with its `client_type_of`
- `ecosim-hpc` depends on the server *and* on every client package, because it imports their
  classes directly: `hpc_main_process` constructs the `Server`, and `ClientManager` starts the
  clients as tasks on the dask cluster
- `ecosim` depends on the server and on the clients that need no extra setup. One install is enough for a local
  run. Its check reads the config files with the readers of the server and the clients
- `integration-tests` depends on all of them, which is why it is excluded from `dev/run_unit_tests.py`

Every internal dependency is pinned to the exact version (`ecosim-common==0.14.0`) and resolved
from the working tree through `[tool.uv.sources]` with `editable = true`. A version bump therefore
has to happen in every `pyproject.toml` at once.

## Module structure

The Python modules are internal and can change: the supported way to use eCoSim is the
[command line](../reference/command-line.md) and the [configuration files](../reference/configuration-files.md).
The one exception is `ecosim_server.results`. It reads the results of a run as one table. Scripts of users call
`read_file_results`, `read_database_results`, `ResultTable` and `ResultColumn`. Keep these names.

### `ecosim_common`

| Package | Contains |
| --- | --- |
| `communication/channel` | `ESPChannel`, the transport abstraction, plus its message types |
| `communication/dask` | `DaskChannel` — transport over a dask cluster |
| `communication/socket` | `TCPSocket` — transport over a plain TCP socket |
| `communication/binary_message` | Framing: header, message assembly |
| `communication/data` | The payloads: meta data, interface settings, step requests |
| `config` | `AppConfig` and `EcosimArgumentParser` (command-line options), `ConfigParser` (ini files), `DatabaseType`, interface ids |
| `client` | `Client` — the base class every client subproject specialises. `SimulatorDirectory` finds the folder of each simulator of a run, usually in `Modules` |
| `simulation` | Interface identity: `InterfaceId`, `ModelInterfaceId`, `SimulatorInterfaceId` |
| `tech` | Infrastructure: logging, threading, json, datetime |
| `tech/structures` | `ESPQueue`, `ESPList`, `ESPMap`, … each with a thread and a dask backend, chosen by `ESPStructureType`. Shared state uses them, so the same code runs on threads or on dask workers |

### `ecosim`

| Module | Contains |
| --- | --- |
| `main.py`, `command.py` | The dispatcher and `COMMANDS`. A command is a module with `build_parser()` and `main(passed_arguments) -> int`. It is imported only when it runs. `ecosim --help` needs neither the server nor fmpy |
| `simulation_directory.py` | `SimulationDirectory`: where the files of a simulation are |
| `simulation_options.py`, `simulation_command_line.py` | The options that the commands share and `RunOptions`. Many are options of the server |
| `run_length.py` | `--step-size` and `--duration` with a unit, like `15min` |
| `server_arguments.py` | The arguments a command passes to `ecosim-server`, with the options after `--` |
| `report_lines.py` | The lines that several commands print: the table of the simulators and the length of a run |
| `new/` | `ecosim new`. `SimulationModel` reads an FMU. `InputConnections` connects the inputs to the outputs by name or by `--connect`. `loops.py` finds models that form a loop without a logical delay. `NewSimulationFiles` writes the files |
| `check/` | `ecosim check`. `SimulationCheck` loads a simulation with the readers of the server and the clients and collects every problem |
| `run_directory.py` | `RunDirectory`: the folder of one run, `SIMULATION/results/<start time>/` with the results, a copy of `simulation.json` and `logs/` |
| `run/` | `ecosim run`. `LocalRun` starts the server and the clients, each in its own process group. `RunWatch` stops all of them when one fails or on a signal |
| `results/` | `ecosim results`. Finds the results of a folder or a server config, reads them with `ecosim_server.results` and prints the overview or writes the CSV file |

### `ecosim_server`

| Module | Contains |
| --- | --- |
| `main.py`, `server.py`, `server_state.py` | Entry point and the server lifecycle |
| `run_summary.py`, `progress_logger.py` | The summary at the end of a run and the logger of the progress lines |
| `client/` | One `ClientConnection` per client, message buffer and subscriptions |
| `simulation/` | `SimulationExecutor`, the step loop and its progress line, value history, restore |
| `simulation/state/` | `SimulationStateRepository` and its two implementations |
| `measurement/` | `MeasurementRepository` — the simulation results |
| `results/` | `read_file_results` for files and `read_database_results` for PostgreSQL. Both return the stored results of a run as one table with a column per interface. `to_pandas_data_frame()` needs the extra `ecosim-server[pandas]` |
| `data/` | `Repositories` — the aggregate the rest of the server is given |
| `tech/db/` | SQLAlchemy and file backends |
| `config/` | `CLIArguments`, `ServerConfig`, `SimulationConfig` |

### The clients

Every client subproject follows the same shape, so a new client is easy to place:

```
main.py               the console script
<name>_client.py      the Client subclass: talks to the server and drives the model
<name>_config.py      the model specific configuration
```

The FMU clients name the last one `fmu2_simulator_config.py` / `fmu3_simulator_config.py`; the
others use `matlab_config.py`, `pyro_config.py` and `python_config.py`. The Python client also has
`python_model.py` with the methods of a model and `model_import.py` to import it.

## Communication

Clients never talk to each other: every value goes from a client to the server, and from there to
the clients it is connected to. That is what lets the server delay connections and keep all
clients on the same step. Pyro5 is a kind of client, not a protocol.

The server and the clients never speak a transport directly. They use `ESPChannel`, and
`ESPChannel.for_protocol()` picks the implementation from the configured
`CommunicationProtocol`:

| Protocol | In ini files | On the command line | Implementation |
| --- | --- | --- | --- |
| TCP socket | `TCP_SOCKET` | `tcp_socket` or `TCP_SOCKET` | `communication/socket/tcp_socket.py` |
| Dask | `DASK` | `dask` or `DASK` | `communication/dask/dask_channel.py` |

The ini files take the member name, because `ConfigParser.get_enum` looks the value up by name. The
command line goes through `CommunicationProtocol.of()`, which ignores the case.

`MessageType` is the protocol vocabulary. It is deliberately restricted to the values 0–255, so
that one byte carries it regardless of the transport underneath.

**The server initiates every exchange.** It sends a message and then waits for a reply of the
*same* `MessageType` — the type names the exchange, not a direction. `CorrelationId` matches a
reply to its request, which is what allows the steps to be sent from separate threads.

| Message | The server asks | The client replies |
| --- | --- | --- |
| `CLIENT_META_DATA_REQUEST` | who are you | its meta data |
| `INTERFACE_REQUEST` | which interfaces do you expose | its `ModelInterfaceIds`, which the server validates against the simulation config |
| `INTERFACE_SETTINGS` | here is your interface configuration | acknowledgement |
| `SIMULATION_SETUP` | here is the step size | acknowledgement |
| `SIMULATION_START` | start now | its start values |
| `SIMULATION_STOP` | stop now | acknowledgement |
| `SIMULATION_STEP` | advance one step with these inputs | its outputs |
| `SIMULATION_STEP_BATCH` | advance several steps | the outputs of the last step |
| `PING` | are you alive | `PING` |

On the client side `Client._handle_message` dispatches over the same enum with an `assert_never`
default, so `mypy` rejects a new `MessageType` until the client handles it. The server has no such
single dispatch point: it sends and awaits each type where it needs it.

`SIMULATION_STEP_BATCH` exists for restoring aborted runs. A restore continues after the last step that every
client completed: each client gets its stored steps up to that step as one batch, and the stored rows after it
are removed, because those steps run again.

## Storage

The server writes through `Repositories`, an abstract aggregate: a `SimulationStateRepository`, a
`ServerTimeMeasurementRepository` and one `MeasurementRepository` per client.
`create_repositories()` chooses the implementation from the `type` in the `[database]` section of
the server ini:

| `DatabaseType` | Implementation | Needs |
| --- | --- | --- |
| `postgres` | `RepositoriesDB` | a PostgreSQL/TimescaleDB instance |
| `file` | `RepositoriesFileBased` | a writable directory, one JSON lines file per module |

Both are exercised end to end by the [Docker example](../guides/docker.md). The code that uses them never sees
the difference. The implementations are in `data/`, `measurement/`, `simulation/state/` and `tech/db/`.
`tech/db/` also holds what they share: the database connection and base classes, the PostgreSQL setup and
`FileRepository`. The final state is stored as `finished` in the database and as `Finished` in the file backend.
The file backend also copies the run's `simulation.json` into its directory. The results can then be read without
the original config.

## Entry points

Each deployable subproject declares a console script:

| Command | Module |
| --- | --- |
| `ecosim` | `ecosim.main:main` |
| `ecosim-server` | `ecosim_server.main:main` |
| `ecosim-client-fmu-v2` | `ecosim_client_fmu_v2.main:main` |
| `ecosim-client-fmu-v3` | `ecosim_client_fmu_v3.main:main` |
| `ecosim-client-matlab` | `ecosim_client_matlab.main:main` |
| `ecosim-client-pyro5` | `ecosim_client_pyro5.main:main` |
| `ecosim-client-python` | `ecosim_client_python.main:main` |
| `ecosim-hpc` | `ecosim_hpc.main:main` |

`ecosim-hpc` needs `mpirun` or a running Dask scheduler, see the [HPC notes](tech/hpc-cheat-sheet.md).

Every `main` is wrapped in `exits_with_one_line_errors` from `ecosim_common/tech/one_line_errors.py`. The dispatcher
does that for the `ecosim` commands. Without `--debug`, an error prints one line on stderr instead of a traceback
and the command exits with code 1.

Each console script reads its options with a `CLIArguments` class, an `AppConfig` from `ecosim-common`. Each option is
an `AppConfigParameter` with a group. `--help` and the [command-line reference](../reference/command-line.md) show a
group as a section. The server's options are in `ecosim_server/config/cli_parameters.py` and
`database_cli_parameters.py`. `ecosim-hpc` and the `ecosim` commands reuse them. The `transform` of a parameter
converts and checks its value. A bad value ends the command with a usage error and exit code 2.
