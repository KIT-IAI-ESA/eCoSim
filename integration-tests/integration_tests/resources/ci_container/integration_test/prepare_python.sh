#!/bin/bash

source /integration_test/config.sh

echo "Preparing python..."
cd "$PYTHON_BASE_DIR" || exit 123
"$PYTHON_CMD" -m venv venv
source venv/bin/activate
pip install --upgrade pip
echo "Preparing python... installing ecosim-common..."
pip install ecosim-common/
echo "Preparing python... installing ecosim-client-fmu-v2..."
pip install ecosim-client-fmu-v2/
echo "Preparing python... installing ecosim-server..."
pip install ecosim-server/
echo "Preparing python...end"
