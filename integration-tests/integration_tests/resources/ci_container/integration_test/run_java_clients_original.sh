#!/bin/bash

source /integration_test/config.sh

CLIENT_JAR=/integration_test/ecosim_java/FmuVariation-0.0.1-SNAPSHOT-shaded.jar
BASE_DIR_MODULES=$1

shift
MODULES=("$@")

"$IT_BASE_DIR"/run_java_clients.sh "$CLIENT_JAR" "$BASE_DIR_MODULES" "${MODULES[@]}" &
