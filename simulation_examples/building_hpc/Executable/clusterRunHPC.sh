#!/bin/bash
#SBATCH --ntasks=4
#SBATCH --time=1
#SBATCH --mem=2GB
#SBATCH --job-name=ecosim-test

module load devel/miniforge/25.3.1-python-3.12
module load mpi/openmpi/5.0-gnu-14.2
conda activate eCoSim

ECOSIM_DIR="$HOME/ecosim" #Change to location of eCoSim as need

source $ECOSIM_DIR/simulation_examples/.venv/bin/activate

#set ecosim location
#create conda env and install uv and postgresql, perhaps seperate script
#activate sim env and run

#Initialize postgres server
PG_SERVER_DIR="test"
if [ ! -d "$PG_SERVER_DIR" ]; then
    initdb -D $PG_SERVER_DIR
fi

#connect to postgres server
pg_ctl start -D $PG_SERVER_DIR -l $PG_SERVER_DIR/logfile -o "-F -p 5432"

#create databank
if ! psql -lqt | cut -d \| -f 1 | grep -wq sim_control; then
    createdb sim_control
fi

mpirun --bind-to core --map-by core uv run $ECOSIM_DIR/ecosim-hpc/ecosim_hpc/main.py --server-config ../server/preferences.ini --debug --simulation-config ../server/simulation.json --simulator-dir ../Modules/ --steps 100 --database-schema temp_schema --database-drop-existing-schema


pg_ctl stop -D $PG_SERVER_DIR
