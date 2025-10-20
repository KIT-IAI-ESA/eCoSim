# Running this example on bwUniCluster
This example is similar to the already existing building one, with the server and client bash scripts contained into a single script here for executing with SLURM, the cluster's queuing system. Additionally there is a small change to `server/preferences.ini` to account for where the PostgreSQL server is located.

There are two scripts here: `clusterSetup.sh` and `clusterRun.sh`. The first sets up the conda and virtual environments to run the simulation and effectively only needs to be executed once. This will also install the relvant packages needed including PostgreSQL. The second script is for submitting the simulation to the cluster node. This is currently configured for SLURM and to be executed with 4 cores on a node within 1 minute.


## Setting up and running the simulation:
1. First create a workspace for running the simulation in and get access to it from the home directory:
    - `ws_allocate building_test 30 ` - this will create a workspace for 30 days on the cluster.
    - `mkdir workspaces` - make a directory where the link to the workspaces will go.
    - `ws_register workspaces` - creates the link.
    - `cd workspaces/pfs7wor9/<user>-building_test` - change to the workspace. `<user>` will be your cluster username. For KIT users, this will be `ka_<KIT_ID>`.

2. Copy `building_hpc` to the workspace.
3. Edit `clusterSetup.sh` as needed to reflect the location of the eCoSim directory on your system.
4. Run `clusterSetup.sh` with `bash clusterSetup.sh`.
5. Edit `clusterRun.sh` as needed to reflect the location of the eCoSim directory.
6. Submit the simulation to the queue with `sbatch -p <partition> clusterRun.sh`. For this test on bwUniCluster I recommend using `dev_cpu` or `dev_cpu_il` for the partition due to the short time needed for the simulation to run.

After the simulation has ran, you will have a directory called test where the SQL database sim_control can be found with the regular PostgreSQL commands, for example:

```
conda activate eCoSim
pg_ctl start -D test -l test/logfile -o "-F -p 5432"
psql -d sim_control
# ....Do your SQL calls as needed....
sim_control=# \q
pg_ctl stop -D test
```
