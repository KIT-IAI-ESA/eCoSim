---
title: HPC cluster
description: Run the building example on bwUniCluster with SLURM.
---

# HPC cluster

The `simulation_examples/building_hpc` example runs the building simulation on bwUniCluster. The
server and the clients are started by one script, which is submitted to SLURM, the cluster's
queuing system. `server/preferences.ini` points at the PostgreSQL server on the cluster.

The example has two scripts in `building_hpc/Executable/`:

- `clusterSetup.sh` sets up the conda and virtual environments and installs the packages, including
  PostgreSQL. It only needs to run once.
- `clusterRun.sh` submits the simulation to a cluster node. It is configured for SLURM, with 4 cores
  on one node for 1 minute.

## Set up and run

1. Create a workspace for the simulation and link it into your home directory:

   ```shell
   ws_allocate building_test 30   # a workspace for 30 days
   mkdir workspaces
   ws_register workspaces
   cd workspaces/pfs7wor9/<user>-building_test
   ```

   `<user>` is your cluster user name. For KIT users this is `ka_<KIT_ID>`.

2. Copy `building_hpc` into the workspace.
3. Edit `clusterSetup.sh` so it points at the eCoSim directory on your system.
4. Run it: `bash clusterSetup.sh`
5. Edit `clusterRun.sh` so it points at the eCoSim directory.
6. Submit the simulation: `sbatch -p <partition> clusterRun.sh`. For this short test, the
   partitions `dev_cpu` or `dev_cpu_il` are a good choice.

## Look at the results

After the run, the PostgreSQL database `sim_control` is in the directory `test`:

```shell
conda activate eCoSim
pg_ctl start -D test -l test/logfile -o "-F -p 5432"
psql -d sim_control
# run your queries, then leave psql with \q
pg_ctl stop -D test
```

## See also

- [HPC cheat sheet](../development/tech/hpc-cheat-sheet.md): batch and interactive mode with Dask-MPI
- [Command-line options](../reference/command-line.md#hpc) of the HPC entry point
