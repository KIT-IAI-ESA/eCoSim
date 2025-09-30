# ECOSIMPY_DIR must be identical with the GIT_CLONE_PATH in .gitlab-ci.yml
ECOSIMPY_DIR=/builds/ecosimpy
PYTHON_BASE_DIR=$ECOSIMPY_DIR/ecosim
IT_BASE_DIR=/integration_test
IT_RESULTS="$IT_BASE_DIR/results"
FINAL_RESULT="$IT_RESULTS/result"
IT_LOGS="$IT_BASE_DIR/logs"
EXPECTED_DIR="$IT_BASE_DIR/expected"
EXCLUDE_COLUMNS="'timestamp', 'state_id', 'ensemble_members_id', 'ensembles_id'"
DB_INIT_CHECK_FILE=/integration_test/db_init.done
SERVER_JAR=/integration_test/ecosim_java/SimulationMasterRun-0.0.1-SNAPSHOT-shaded.jar
PYTHON_CMD=python3

mkdir -p $IT_RESULTS
mkdir -p $IT_LOGS


wait_for_server() {
  echo 0 > "/tmp/master_available"
  timeout "$1" bash -c '
  while [ $(cat "/tmp/master_available") -eq 0 ]; do
    echo "Waiting for master..."
    sleep 1
    nc -z localhost 1234
    if [ $? -eq 0 ]; then
      echo 1 > "/tmp/master_available"
    fi
  done'
  if [ "$(cat "/tmp/master_available")" -eq 0 ]; then
    echo "ERROR: Master took too long to start."
    exit 123
  fi
  rm /tmp/master_available
}


wait_for_test_finish() {
  echo 0 > "/tmp/test_finished"
  # Check if the first row in the column 'state' of the 'simulation_state' table has the value 'finished'
  timeout "$1" bash -c 'until [ $(cat "/tmp/test_finished") -eq 1 ]; do
        echo "Waiting for test to finish...";
        sleep 2
        result=$(psql -d postgres -Atc "SELECT state FROM simulation_state LIMIT 1;")
        if [ "$result" == "finished" ]; then
          echo 1 > "/tmp/test_finished"
        fi
      done'
  if [ "$(cat "/tmp/test_finished")" -eq 0 ]; then
    echo "ERROR: Test took too long (more than $1)."
    exit 123
  fi
  rm /tmp/test_finished
  echo "Test finished."
}


wait_for_db_init_and_availability() {
  echo "Waiting for DB init and availability..."
  FILE_EXISTS=0
  export FILE_EXISTS
  timeout 60s bash -c '
  while [ $FILE_EXISTS -eq 0 ]; do
    echo "Waiting for DB to be initialized..."
    sleep 1
    if [ -f $DB_INIT_CHECK_FILE ]; then
      FILE_EXISTS=1
    fi
  done' || (echo "ERROR: Initialization of DB took too long." && exit 123)

  echo "Waiting a short time to let the DB restart"
  sleep 4s

  wait_for_postgres_start
}


wait_for_postgres_start() {
  (timeout 15s bash -c 'until pg_isready; do \
        echo "Waiting for PostgreSQL to start..."; \
        sleep 1; \
      done' && echo "PostgreSQL is ready.") || (echo "ERROR: Failed to start PostgreSQL" && exit 123)
}
