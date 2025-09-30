#!/bin/bash

source /integration_test/config.sh

BASE_DIR=$1
shift 1
MODULES=("$@")

SIMDB_ARGS=()
for part in "${MODULES[@]}"; do
  SIMDB_ARGS+=("module_${part}")
done

EVALDB_ARGS=()
for part in "${MODULES[@]}"; do
  EVAlDB_ARGS+=("eval_${part}_0")
done

#$IT_BASE_DIR/check_simdb.sh "$BASE_DIR/expected" "ensemble_members" "ensembles" "simulation_state" "${SIMDB_ARGS[@]}"
$IT_BASE_DIR/check_simdb.sh "$BASE_DIR/expected" "simulation_state" "${SIMDB_ARGS[@]}"
#$IT_BASE_DIR/check_evaldb.sh "eval_master_0" "performance_master" "${EVALDB_ARGS[@]}"

$IT_BASE_DIR/check_results.sh
