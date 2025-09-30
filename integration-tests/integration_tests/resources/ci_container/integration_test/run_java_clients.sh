#!/bin/bash

source /integration_test/config.sh

CLIENT_JAR=$1
BASE_DIR_MODULES=$2

shift 2
MODULES=("$@")

# Function to handle script interruption
cleanup() {
    echo "Interrupt signal received, terminating background processes..."
    # Kill all background processes
    kill $(jobs -p)
    exit 1
}

# Trap the SIGINT signal (Ctrl+C)
trap cleanup SIGINT

echo "Starting Java clients in $BASE_DIR_MODULES"

# Start the background processes
pids=()
for module in "${MODULES[@]}"; do
  java -jar "$CLIENT_JAR" "$BASE_DIR_MODULES/${module}_preferences_linux.ini" > "$IT_LOGS/java_module_${module}.log" 2>&1 &
  pids+=($!)
done

# Wait for the background processes to finish
wait "${pids[@]}"
