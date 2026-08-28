# eCoSim

eCoSim couples independent simulation models into one co-simulation. A **server** owns the clock
and the data flow; one **client** per model advances it step by step.

```
weather ──T_out, dir_sol_irradiance──▶ house ──room_temperature──▶ heating ─────┐
                                        ▲                          ventilation ─┘
                                        └──── control signals ──────────────────┘
```

Models are plugged in through a client: FMI 2.0, FMI 3.0, Matlab or Pyro5. The server stores the
results either in PostgreSQL/TimescaleDB or as JSON lines on disk.

## Use eCoSim

- [Use packages](use_packages.md) — install the `ecosim-*` packages from the registry
- [Release history](release_history.md)

## Develop eCoSim

- [Project setup](dev/project_setup.md) — get the monorepo running locally
- [Architecture](dev/architecture.md) — the subprojects, the protocol and the storage backends
- [Dev notes](dev/developing.md) — dependencies and running the tests

## Technical notes

- [HPC cheat sheet](dev/tech/hpc.md)
- [Multi threading with fmpy](dev/tech/multi_threading_fmpy.md)
- [Performance: original HPC vs common abstraction](dev/performance/2026-07-28/2026-07-28_original_hpc_vs_common_abstraction.md)
