---
name: orientation
description: Map of the ecosim codebase - how server, clients and common fit together, where the communication, configuration and storage layers live. Use when starting work in an unfamiliar part of the repository or looking for where something belongs.
---

# Orientation

eCoSim couples independent simulation models (FMU, Matlab, …) into one co-simulation. A
**server** owns the clock and the wiring; each model runs in a **client** process. Server and
clients exchange interface values once per simulation step.

## The three layers

```
ecosim-common          shared by both sides: protocol, config, primitives
   |
   +-- ecosim-server   clock, wiring, storage
   +-- ecosim-client-* one per model kind (fmu-v2, fmu-v3, matlab, pyro5)
```

A client never talks to another client. Values flow client → server → client, which is what
makes the delay handling and the step barrier possible.

## ecosim-common

| Path | What lives there |
|---|---|
| `communication/channel/` | `ESPChannel` — the transport abstraction both sides program against |
| `communication/socket/` | TCP implementation |
| `communication/dask/` | dask implementation, for distributed/HPC runs |
| `communication/data/` | the wire payloads (`ClientSimStepData`, `ProtocolInterfaceValue`, …) |
| `config/` | `ClientID`, `InterfaceType`, `DatabaseType`, ini parsing |
| `simulation/` | the id types: `InterfaceId`, `ModelInterfaceId`, `SimulatorInterfaceId` |
| `tech/structures/` | `ESPQueue`, `ESPList`, `ESPMap`, … each with a thread and a dask backend |

`CommunicationProtocol` has exactly two members: `TCP_SOCKET` and `DASK`. Pyro5 is a *client
kind*, not a protocol — do not confuse the two.

The `tech/structures` and `tech/parallel` packages exist because the same server code has to
run against plain threads or across dask workers. `ESPStructureType` selects the backend, so
code that needs shared state should use these wrappers rather than a bare `queue.Queue`.

## ecosim-server

| Path | What lives there |
|---|---|
| `main.py` | entry point: reads config, builds repositories, starts the server |
| `server.py`, `server_state.py` | lifecycle |
| `client/` | one `ClientConnection` per client, message buffering and subscriptions |
| `simulation/simulation_executor.py` | the step loop |
| `simulation/interface_value_history*.py` | values over time, including delayed connections |
| `simulation/state/` | `SimulationState` and its repository |
| `data/repositories*.py` | storage, see below |
| `measurement/` | the recorded results per client |

## Storage

`Repositories` is an abstract bundle of three repositories (simulation state, server time
measurement, and one measurement repository per client). `create_repositories()` in
`data/repositories.py` dispatches on `DatabaseType`:

- `POSTGRES` → `RepositoriesDB`, SQLAlchemy against TimescaleDB
- `FILE` → `RepositoriesFileBased`, append-only JSON lines per simulator

Anything reading results must work against the abstract types, because both backends are
supported and exercised. Two known divergences: the database returns UTC-aware timestamps
while the file backend keeps naive ones, and the final state serialises as `finished`
(database) versus `Finished` (file).

## Configuration

A run is described by two files, both passed on the command line:

- a **server ini** — host, port, and the `[database]` section
- a **simulation json** — the clients, their interfaces and how they are connected

CLI flags such as `--database-type` override the ini through `DbConfigOverwrite`.
`dev/docker/example/*/config/` holds a complete working pair of both.

## Where to look for behaviour

Tests are the readable specification. `integration-tests/integration_tests/server_client/`
runs a real server against a real client over every protocol and every storage backend via
fixtures, and is the fastest way to understand an end-to-end run.
`ecosim-test-common` provides those fixtures plus the FMU model resources.

## The human facing counterpart

`docs/dev/architecture.md` covers the same ground for humans and is published as a site (see
`mkdocs.yml`). This skill is the working map; that page is the documentation. When the structure
changes, both have to change.
