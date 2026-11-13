#!/bin/bash
#SBATCH --ntasks=4
#SBATCH --time=1
#SBATCH --mem=2GB
#SBATCH --job-name=ecosim-test

module load devel/miniforge/25.3.1-python-3.12
module load mpi/openmpi/5.0-gnu-14.2
conda activate eCoSim

ECOSIM_DIR="$HOME/ecosim" #Change to location of eCoSim as need

# shellcheck disable=SC1091
source "$ECOSIM_DIR/simulation_examples/.venv/bin/activate"

#set ecosim location
#create conda env and install uv and postgresql, perhaps seperate script
#activate sim env and run

#Initialize postgres server, with a password so other users on the node cannot log in
PG_SERVER_DIR="test"
export PGPASSFILE="$PWD/$PG_SERVER_DIR.pgpass"
export PGREQUIREAUTH=scram-sha-256
if [ ! -d "$PG_SERVER_DIR" ]; then
    PG_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
    if [ -z "$PG_PASSWORD" ]; then
        echo "python3 could not create a password for PostgreSQL." >&2
        exit 1
    fi
    (umask 077 && echo "*:*:*:*:$PG_PASSWORD" > "$PGPASSFILE")
    initdb -D $PG_SERVER_DIR --auth=scram-sha-256 --pwfile=<(echo "$PG_PASSWORD")
elif grep -q "^[^#]*trust" "$PG_SERVER_DIR/pg_hba.conf"; then
    echo "$PG_SERVER_DIR allows logins without a password, it was created by an older version of this script. Delete or rename it and submit again." >&2
    exit 1
fi

#connect to postgres server
pg_ctl start -D $PG_SERVER_DIR -l $PG_SERVER_DIR/logfile -o "-F -p 5432" || exit 1

#create databank
if ! psql -w -lqt | cut -d \| -f 1 | grep -wq sim_control; then
    createdb -w sim_control
fi

mpirun --bind-to core --map-by core uv run "$ECOSIM_DIR/ecosim-hpc/ecosim_hpc/main.py" --server-config ../server/preferences.ini --debug --simulation-config ../server/simulation.json --simulator-dir ../Modules/ --steps 100 --database-schema temp_schema --database-drop-existing-schema


pg_ctl stop -D $PG_SERVER_DIR
