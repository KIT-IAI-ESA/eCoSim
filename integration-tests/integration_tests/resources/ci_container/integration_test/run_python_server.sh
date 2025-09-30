source /integration_test/config.sh

SERVER_DIR=$1
STEPS=$2
CONFIG_JSON=$SERVER_DIR/simulation.json
PREFERENCES_INI=$SERVER_DIR/preferences.ini

echo "Starting Python server with config: $CONFIG_JSON"
cd "$PYTHON_BASE_DIR" || exit 123
source venv/bin/activate
python -m ecosim_server.main --server-config "$PREFERENCES_INI" --debug --simulation-config "$CONFIG_JSON" --steps "$STEPS" --database-name postgres --database-schema public --database-user postgres --database-user-password '' --database-drop-existing-schema
