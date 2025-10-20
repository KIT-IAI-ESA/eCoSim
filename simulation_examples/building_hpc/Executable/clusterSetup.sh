ECOSIM_DIR=$HOME/ecosim #eCoSim directory. Change as needed.

module load devel/miniforge/25.3.1-python-3.12

if ! conda info --envs | grep -wq "eCoSim"; then
    echo "No eCoSim conda environment detected."
    echo "Creating environment and simulation environment."
    conda create --name eCoSim python=3.13
    conda activate eCoSim
    conda install uv postresql
    cd $ECOSIM_DIR/simulation_examples
    uv sync
    echo "Completed!"

elif [ ! -d "$ECOSIM_DIR/simulation_examples/.venv" ]
    echo "conda environment eCoSim already exists but simualtion environment not setup."
    echo "Setting up ..."
    cd $ECOSIM_DIR/simulation_examples
    uv sync
    echo "Completed!"
else
    echo "conda environment eCoSim already exists"
fi
