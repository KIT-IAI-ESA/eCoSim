#!/bin/bash

source /integration_test/config.sh

TABLES=("$@")

# Function to dump selected columns of a table to CSV
dump_table() {
    local table=$1
    local output_file="$IT_RESULTS/simdb_$table.csv"
    echo "dumping table $table to $output_file..."
    # Generate column list excluding the specified columns
    columns=$(psql -d postgres -t -c "SELECT string_agg(column_name, ', ') FROM information_schema.columns WHERE table_name = '$table' AND column_name NOT IN (${EXCLUDE_COLUMNS});")
    # Dump the table to CSV
    psql -d postgres -c "COPY (SELECT $columns FROM $table) TO STDOUT WITH CSV HEADER" > $output_file
    echo "dumping table $table to $output_file...done"
}

# Dump reference state
for table in "${TABLES[@]}"; do
    dump_table $table
done

exit 0
