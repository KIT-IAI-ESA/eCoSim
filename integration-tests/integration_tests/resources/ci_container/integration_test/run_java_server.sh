source /integration_test/config.sh

SERVER_JAR=/integration_test/ecosim_java/SimulationMasterRun-0.0.1-SNAPSHOT-shaded.jar
SERVER_DIR=$1
STEPS=$2
CONFIG_JSON=$SERVER_DIR/simulation.json

echo "Starting Java server with config: $CONFIG_JSON"
cd "$SERVER_DIR" || exit 123
java -jar "$SERVER_JAR" -json "$CONFIG_JSON" -steps "$STEPS" -newdb true > "$IT_LOGS/java_server.log" 2>&1 &
