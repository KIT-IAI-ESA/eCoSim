#!/bin/bash

source /integration_test/config.sh

PG_DATA=/var/lib/pgsql/16/data

if [ ! -f "$DB_INIT_CHECK_FILE" ]; then
  echo "No '$DB_INIT_CHECK_FILE' found - so running basic initialization."
  echo ""

  /usr/pgsql-16/bin/initdb -D "$PG_DATA"

  # Run timescaledb-tune
  timescaledb-tune --quiet --yes

  # Restart PostgreSQL
  pg_ctl -D "$PG_DATA" stop
  pg_ctl -D "$PG_DATA" start
  wait_for_postgres_start

  # Init DB
  psql -d postgres -a -f /integration_test/init-db.sql

  pg_ctl -D "$PG_DATA" stop

  touch $DB_INIT_CHECK_FILE
fi

# Start PostgreSQL normally
pg_ctl -D "$PG_DATA" stop
exec postgres -D "$PG_DATA"
