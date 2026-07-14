# HPC Cheat Sheet

Just quick notes for non-HPC gurus.

## Batch vs. Interactive Mode

### Batch Mode

- in classic HPC
    - write a script, submit it to the queue (and walk away -> i.e. the rest is unattended)
    - the scheduler runs it when resources free up
- in Dask-MPI: the cluster and script are bundled in one program -> it runs from top to bottom and exists

### Interactive Mode

- in classic HPC
    - get a live shell/session and drive things in real time (typing commands, seeing output immediately, ...)
    - 'human in the loop'
- in Dask-MPI
    - cluster runs as a standalone job
    - issue commands on the fly, inspect results, submit more work, add workers, ...

#### Start in Interactive Mode

- `cd ecosim-hpc`
- `uv run ecosim_hpc/main.py --interactive --server-config not_there --simulation-config not_there --simulator-dir not_there --steps 1`
    - you indeed need not provide `server-config`, `simulation-config` or `simulator-dir`
