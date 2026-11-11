---
title: HPC cluster
description: Run the building example on bwUniCluster with SLURM and Dask-MPI.
---

# HPC cluster

The `simulation_examples/building_hpc` example runs the building simulation on bwUniCluster through
`ecosim_hpc/main.py`. One job script is submitted to SLURM, the cluster's queuing system, and starts
everything with `mpirun`. Dask-MPI then turns the MPI ranks into a Dask cluster:

- rank 0 is the Dask scheduler
- rank 1 runs the server
- every other rank is a Dask worker, and the workers run the clients

This batch mode needs `mpirun` and at least 3 ranks. Started without `mpirun` it stops with an error.

The example has these scripts in `building_hpc/Executable/`:

- `clusterSetup.sh` sets up the conda and virtual environments and installs the packages, including
  PostgreSQL. It only needs to run once.
- `clusterRunHPC.sh` is the job script. It starts PostgreSQL, runs the simulation with `mpirun` and
  stops PostgreSQL again. It is configured for SLURM, with 4 tasks for 1 minute: the scheduler, the
  server and 2 workers.
- `clusterRun.sh` is the same job with the plain server and one process per client, without `mpirun`
  and Dask.

`server/preferences.ini` points at the PostgreSQL server the job script starts.

A simulator's directory in `Modules/` holds one model only, because `ecosim_hpc/main.py` chooses the client
by the files in it: an FMU client for each `.fmu` file, the Pyro5 client for `.py` files and the MATLAB
client for `.m` files.

## Set up and run

1. Create a workspace for the simulation and link it into your home directory:

   ```shell
   ws_allocate building_test 30   # a workspace for 30 days
   mkdir workspaces
   ws_register workspaces
   cd workspaces/pfs7wor9/<user>-building_test
   ```

   `<user>` is your cluster user name. For KIT users this is `ka_<KIT_ID>`.

2. Copy `building_hpc` into the workspace and change into `building_hpc/Executable`. The scripts use
   paths relative to it.
3. Edit `ECOSIM_DIR` in `clusterSetup.sh` so it points at the eCoSim directory on your system.
4. Run it: `bash clusterSetup.sh`
5. Edit `ECOSIM_DIR` in `clusterRunHPC.sh` as well.
6. Submit the simulation: `sbatch -p <partition> clusterRunHPC.sh`. For this short test, the
   partitions `dev_cpu` or `dev_cpu_il` are a good choice.

## Choose the network and the threads

By default Dask uses the address of the network with the default route, and every worker has 2 threads.
Add these options to the `mpirun` line of `clusterRunHPC.sh` to change that:

- `--network-interface ib0` uses this network interface, for example InfiniBand instead of Ethernet.
  The job stops right away if a node does not have it. Common names are `enp3s0`, `eno1`, `eth0` and
  `ib0`; `ip link` lists them.
- `--threads-per-worker 4` gives every worker 4 threads. The script binds each rank to one core with
  `--bind-to core`, so those threads share that core unless you change the binding. Keep at least 2
  threads when the job has only one worker: the server waits for new connections in a task that keeps
  one thread busy for the whole run, and with a single thread the clients never start.

## Look at the results

After the run, the PostgreSQL database `sim_control` is in the directory `test` next to the scripts.
The script's `--database-schema` puts the tables into the schema `temp_schema`, and its
`--database-drop-existing-schema` makes the next run replace them:

```shell
module load devel/miniforge/25.3.1-python-3.12
conda activate eCoSim
pg_ctl start -D test -l test/logfile -o "-F -p 5432"
psql -d sim_control
# \dt temp_schema.* lists the tables; run your queries, then leave psql with \q
pg_ctl stop -D test
```

## See also

- [HPC cheat sheet](../development/tech/hpc-cheat-sheet.md): batch and interactive mode with Dask-MPI
- [Command-line options](../reference/command-line.md#hpc) of the HPC entry point
