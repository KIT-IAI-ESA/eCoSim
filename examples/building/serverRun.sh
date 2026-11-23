#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

exec uv run --project .. ecosim-server \
    --server-config server/preferences.ini \
    --simulation-config server/simulation.json \
    --steps 100 \
    --database-schema temp_schema \
    --database-drop-existing-schema \
    "$@"
