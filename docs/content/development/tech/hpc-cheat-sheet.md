# HPC Cheat Sheet

Quick notes for non-HPC users. The [HPC cluster](../../guides/hpc-cluster.md) guide walks through the
example on bwUniCluster.

## Batch vs. Interactive Mode

### Batch Mode

- in classic HPC
  - write a script, submit it to the queue (and walk away -> i.e. the rest is unattended)
  - the scheduler runs it when resources free up
- in Dask-MPI: the cluster and script are bundled in one program -> it runs from top to bottom and exits
  - needs `mpirun` and at least 3 ranks: Dask scheduler, server, one Dask worker
  - without `mpirun` it stops with an error, either `cannot load MPI library` or `Not enough MPI ranks`

#### Start in Batch Mode

`examples/building_hpc/clusterRunHPC.sh` is the complete job script, with PostgreSQL:

- `cd examples/building_hpc`
- set `ECOSIM_DIR` in the script
- `sbatch -p <partition> clusterRunHPC.sh`

The same run without SLURM and PostgreSQL, on a machine with `mpirun`, in the same directory. The results go
to `simulation_results/`:

```shell
mpirun -np 4 uv run ecosim-hpc \
  --server-config server/preferences.ini --simulation-config server/simulation.json \
  --simulator-dir modules/ --steps 100 --database-type file
```

`--network-interface` and `--threads-per-worker` choose the network and the threads per worker, see the
[command-line options](../../reference/command-line.md#hpc).

### Interactive Mode

- in classic HPC
  - get a live shell/session and drive things in real time (typing commands, seeing output immediately, ...)
  - 'human in the loop'
- in Dask-MPI
  - cluster runs as a standalone job
  - issue commands on the fly, inspect results, submit more work, add workers, ...

#### Start in Interactive Mode

`--interactive` starts no cluster, it connects to a running Dask scheduler through the file the scheduler
writes. In `examples/building_hpc`:

1. Start the scheduler and the workers, each in a terminal of its own:
   - with `mpirun`: `mpirun -np 3 uv run dask-mpi --scheduler-file scheduler.json`, which gives a
     scheduler and 2 workers
   - without it, on one machine: `uv run dask scheduler --scheduler-file scheduler.json` and
     `uv run dask worker --scheduler-file scheduler.json --nworkers 2`
2. Start the simulation once `scheduler.json` exists:

   ```shell
   uv run ecosim-hpc --interactive \
     --server-config server/preferences.ini --simulation-config server/simulation.json \
     --simulator-dir modules/ --steps 100 --database-type file
   ```

- `--scheduler-file` sets another path than `scheduler.json` in the current directory; if the file is
  missing, the command stops right away with an error
- `--server-config`, `--simulation-config` and `--simulator-dir` must point at real files, as in batch mode
- a scheduler serves one run: a second run against it hangs, even with new workers, so stop the scheduler and
  the workers and start new ones
