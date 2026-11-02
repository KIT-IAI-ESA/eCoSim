#!/bin/bash
#SBATCH --ntasks=4
#SBATCH --time=1
#SBATCH --mem=2GB
#SBATCH --job-name=ecosim-test

module load devel/miniforge/25.3.1-python-3.12
conda activate eCoSim

ECOSIM_DIR="$HOME/ecosim" #Change to location of eCoSim as need

# shellcheck disable=SC1091
source "$ECOSIM_DIR/simulation_examples/.venv/bin/activate"

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

python3 "$ECOSIM_DIR/ecosim-client-fmu-v2/ecosim_client_fmu_v2/main.py" --config-file ../Modules/house/preferences.ini --debug --simulator-type fmu > log_client1 &
python3 "$ECOSIM_DIR/ecosim-client-fmu-v2/ecosim_client_fmu_v2/main.py" --config-file ../Modules/occupancy/preferences.ini --debug --simulator-type fmu > log_client2 &
python3 "$ECOSIM_DIR/ecosim-client-fmu-v2/ecosim_client_fmu_v2/main.py" --config-file ../Modules/weather/preferences.ini --debug --simulator-type fmu > log_client3 &

python3 "$ECOSIM_DIR/ecosim-server/ecosim_server/main.py" --server-config ../server/preferences.ini --debug --simulation-config ../server/simulation.json --steps 100 --database-schema temp_schema --database-drop-existing-schema


pg_ctl stop -D $PG_SERVER_DIR
