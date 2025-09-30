#!/bin/bash

source /integration_test/config.sh

# e.g. /integration_test/fmus/houses
BASE_DIR=$1
# e.g. 100
STEPS=$2
# e.g. 70s
TEST_TIMEOUT=$3
# e.g. 50s
SERVER_START_UP_TIMEOUT=$4

# Shift the positional parameters to exclude the first four parameters
shift 4
# e.g ("house" "heating" "weather" "ventilation")
MODULES=("$@")

wait_for_db_init_and_availability

"$IT_BASE_DIR"/run_java_server.sh "$BASE_DIR"/server "$STEPS"
wait_for_server "$SERVER_START_UP_TIMEOUT"

"$IT_BASE_DIR"/run_python_clients.sh "$BASE_DIR"/modules "${MODULES[@]}" &

wait_for_test_finish "$TEST_TIMEOUT"

"$IT_BASE_DIR"/eval.sh "$BASE_DIR" "${MODULES[@]}"
