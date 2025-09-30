#!/bin/bash

source /integration_test/config.sh

BASE_DIR=/integration_test/fmus/houses
MODULES=("house" "heating" "weather" "ventilation")
STEPS=$1
TEST_TIMEOUT=${2:-"240s"}
SERVER_START_UP_TIMEOUT=50s

"$IT_BASE_DIR"/run_java_server_python_client_test.sh $BASE_DIR $STEPS $TEST_TIMEOUT $SERVER_START_UP_TIMEOUT "${MODULES[@]}"
