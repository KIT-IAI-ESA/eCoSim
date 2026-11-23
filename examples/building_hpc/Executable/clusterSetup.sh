#!/bin/bash
# shellcheck disable=SC2164

ECOSIM_DIR=$HOME/ecosim #eCoSim directory. Change as needed.

module load devel/miniforge/25.3.1-python-3.12
module load mpi/openmpi/5.0-gnu-14.2

if ! conda info --envs | grep -wq "eCoSim"; then
    echo "No eCoSim conda environment detected."
    echo "Creating environment and simulation environment."
    conda create --name eCoSim python=3.13
    conda activate eCoSim
    conda install uv postgresql
    cd "$ECOSIM_DIR/examples"
    uv sync
    echo "Completed!"

elif [ ! -d "$ECOSIM_DIR/examples/.venv" ]; then
    echo "conda environment eCoSim already exists but simualtion environment not setup."
    echo "Setting up ..."
    conda activate eCoSim
    cd "$ECOSIM_DIR/examples"
    uv sync
    echo "Completed!"
else
    echo "conda environment eCoSim already exists"
fi
