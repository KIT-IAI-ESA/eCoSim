#!/bin/bash

source /integration_test/config.sh

EXPECTED_DIR=$1
# Shift the positional parameters to exclude the first one
shift
SIMDB_TABLES=("$@")

$IT_BASE_DIR/dump_simdb_tables.sh "${SIMDB_TABLES[@]}"

# Compare the current state with the expected state
for table in "${SIMDB_TABLES[@]}"; do
    DIFF_OUTPUT="$IT_RESULTS/diff_simdb_$table.txt"
    FAIL_MARKER="$IT_RESULTS/fail_simdb_$table"
    EXPECTED="$EXPECTED_DIR/simdb_${table}.csv"
    ACTUAL="$IT_RESULTS/simdb_$table.csv"

    if [ ! -f "$EXPECTED" ]; then
        echo "Expected file $EXPECTED does not exist. Skipping comparison for table $table."
        echo "Expected file is missing" > $FAIL_MARKER
        continue
    fi

    if [ ! -f "$ACTUAL" ]; then
        echo "Actual file $ACTUAL does not exist. Skipping comparison for table $table."
        echo "Actual file is missing" > $FAIL_MARKER
        continue
    fi

    diff "$EXPECTED" "$ACTUAL" > "$DIFF_OUTPUT"
    if [ -s "$DIFF_OUTPUT" ]; then
        echo "Differences found in table $table between the current state and the expected state."
        echo "Differences found - check $DIFF_OUTPUT" > $FAIL_MARKER
        continue
    fi
    echo "The current state matches the expected state for table $table."
done
