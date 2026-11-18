---
title: HPC cluster
description: Run the building example on bwUniCluster with SLURM and Dask-MPI.
---

# HPC cluster

The `simulation_examples/building_hpc` example runs the building simulation on bwUniCluster with the
`ecosim-hpc` command. One job script is submitted to SLURM, the cluster's queuing system, and starts
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

`server/preferences.ini` points at the PostgreSQL server the job script starts. Its user name and password
are empty, so the server logs in as your cluster user with the password from `test.pgpass`, see below.

A simulator's folder in `modules/` has one model. `ecosim-hpc` chooses the client by the files in it:

- the Python client if its `preferences.ini` has `model` in a `[python]` section
- otherwise an FMU client for an `.fmu` file, the MATLAB client for `.m` files or the Pyro5 client for
  `.py` files

Two FMUs or model files of different kinds in one folder stop the job before any client starts.

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
6. If an FMU simulator has a `[start_values]` section, check it on the login node now. A client that
   cannot start on its worker does not stop the job. The server waits for it until the job runs out of
   time. A typo in a start value is enough for that. First run the lines of `clusterRunHPC.sh` from
   `module load` to `source` with your `ECOSIM_DIR`. Your shell then has the environment of the job. In
   `building_hpc/Executable`:

   ```shell
   uv run ecosim-client-fmu-v2 --config-file ../modules/house/preferences.ini --validate-fmu-file-only
   ```

   It reads the FMU and the start values and starts nothing. Use `ecosim-client-fmu-v3` for an FMI 3.0 FMU.
7. In the same shell and folder, check the whole simulation with the options of the job:

   ```shell
   uv run ecosim check .. --database-type postgres --steps 100
   ```

   It lists every problem in the config files, the simulator folders and the start values, see
   [Run a simulation](run-a-simulation.md#check-the-simulation).
8. Submit the simulation: `sbatch -p <partition> clusterRunHPC.sh`. For this short test, the
   partitions `dev_cpu` or `dev_cpu_il` are a good choice.

The first run creates the PostgreSQL data directory `test` next to the scripts. Other users on the same
node can reach this PostgreSQL server, so it only lets in logins with a password. The script creates a
random password, keeps it in `test.pgpass`, a file only you can read, and points `PGPASSFILE` at it, so
`psql`, `createdb` and the server find it. A `test` directory from an older version of the scripts lets
everyone in without a password, so the job stops with a message: delete or rename `test` and submit again.

## What the job prints

The job writes its output to the SLURM file `slurm-<job id>.out` next to the scripts. The server prints
its settings and a progress line from time to time. At the end it prints SIMULATION FINISHED or
SIMULATION FAILED with the steps, the simulated period and where the results are. `clusterRun.sh` writes
the output of the clients to `log_client1` to `log_client3` instead.

The job scripts pass `--debug`. That makes the SLURM file long. `grep -v ' - DEBUG - ' slurm-<job id>.out`
leaves out the debug messages.

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

## Pyro5 simulators

The Dask scheduler places a Pyro5 client on any worker, so it can run on any node of the job. The Pyro object it
connects to therefore has to be reachable from every node:

- `pyro_host` in the simulator's `preferences.ini` is a host name or IP address that every node can reach, not
  `localhost` or `127.0.0.1`
- the Pyro daemon listens on that address, not on `localhost`, and the cluster's network lets the nodes reach
  `pyro_port`
- the process with the Pyro object runs before the job starts the simulation; eCoSim does not start it

[Pyro5 client](pyro5-client.md#reach-the-pyro-object) shows how to start the daemon.

## Python simulators

A model for the [Python client](python-client.md) needs none of this. The client runs it on any worker.
The packages the model imports have to be installed in the environment of the job. Two models in different
folders need modules with different names, see [On an HPC cluster](python-client.md#on-an-hpc-cluster).

## Look at the results

After the run, the PostgreSQL database `sim_control` is in the directory `test` next to the scripts.
The script's `--database-schema` puts the tables into the schema `temp_schema`, and its
`--database-drop-existing-schema` makes the next run replace them. `ecosim results` shows every output and
writes the values to `results.csv`, see [Read the results](results.md). Use `psql` for your own queries. Both
read the password from `test.pgpass`. In `building_hpc/Executable`, with your `ECOSIM_DIR` as in
`clusterRunHPC.sh`:

```shell
module load devel/miniforge/25.3.1-python-3.12
conda activate eCoSim
ECOSIM_DIR="$HOME/ecosim"
source "$ECOSIM_DIR/simulation_examples/.venv/bin/activate"
export PGPASSFILE="$PWD/test.pgpass"
pg_ctl start -D test -l test/logfile -o "-F -p 5432"
uv run ecosim results --server-config ../server/preferences.ini --simulation-config ../server/simulation.json \
    --database-schema temp_schema --csv results.csv
psql -d sim_control
# \dt temp_schema.* lists the tables; run your queries, then leave psql with \q
pg_ctl stop -D test
```

## See also

- [HPC cheat sheet](../development/tech/hpc-cheat-sheet.md): batch and interactive mode with Dask-MPI
- [Command-line options](../reference/command-line.md#hpc) of `ecosim-hpc`
