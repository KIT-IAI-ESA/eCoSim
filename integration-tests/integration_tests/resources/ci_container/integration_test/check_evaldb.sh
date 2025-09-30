#!/bin/bash

source /integration_test/config.sh

EVALDB_TABLES=("$@")

# Function to check if a table exists and has at least one entry
check_table() {
    local table=$1
    local table_exists
    local table_count
    local FAIL_MARKER="$IT_RESULTS/fail_evaldb_$table"

    echo "Checking in EvalDB table $table"

    # Check if the table exists
    table_exists=$(psql -d evaldb -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table');")
    table_exists=$(echo "$table_exists" | xargs)  # Trim whitespace

    if [ "$table_exists" != "t" ]; then
        echo "EvalDB: Table $table does not exist."
        echo "EvalDB: Table $table does not exist." > "$FAIL_MARKER"
        return 1
    fi

    # Check if the table has at least one entry (sometimes the entries need some time to be written, so we need to retry)
    retry_counter=0
    table_count=0
    while [ "$table_count" -eq 0 ] && [ $retry_counter -lt 60 ]; do
      table_count=$(psql -d evaldb -t -c "SELECT COUNT(*) FROM $table;")
      table_count=$(echo "$table_count" | xargs)  # Trim whitespace
      retry_counter=$((retry_counter + 1))
      if [ "$table_count" -eq 0 ]; then
        echo "Table ${table} exists - but has no entries, yet. We give the server some more time to write to DB."
        sleep 1
      fi
    done

    if [ "$table_count" -eq 0 ]; then
        echo "EvalDB: Table $table exists BUT HAS NO ENTRIES."
        echo "EvalDB: Table $table exists but has no entries." > "$FAIL_MARKER"
        return 1
    else
        echo "EvalDB: Table $table exists and has entries."
        return 0
    fi
}

# Iterate over the tables and check each one
for table in "${EVALDB_TABLES[@]}"; do
    check_table "$table"
done
