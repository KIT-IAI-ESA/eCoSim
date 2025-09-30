#!/bin/bash

source /integration_test/config.sh

# Function to handle script interruption
cleanup() {
    echo "Interrupt signal received, terminating background processes..."
    # Kill all background processes
    kill $(jobs -p)
    exit 1
}

# Trap the SIGINT signal (Ctrl+C)
trap cleanup SIGINT

BASE_DIR_MODULES=$1
shift
MODULES=("$@")

cd $ECOSIMPY_DIR/ecosim
source venv/bin/activate

# Start the background processes
echo "Starting clients..."
pids=()
for module in "${MODULES[@]}"; do
  python -m ecosim_client_fmu_v2.main --debug --config-file "$BASE_DIR_MODULES/${module}_preferences_linux.ini" > "$IT_LOGS/python_module_${module}.log" 2>&1 &
  pids+=($!)
done

# Wait for the background processes to finish
wait "${pids[@]}"
