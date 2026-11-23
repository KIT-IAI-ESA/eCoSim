#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

process_ids=()
for module in house occupancy weather; do
    uv run --project ../.. ecosim-client-fmu-v2 \
        --config-file "../modules/$module/preferences.ini" \
        "$@" &
    process_ids+=("$!")
done
trap 'kill "${process_ids[@]}" 2>/dev/null || true' INT TERM

exit_status=0
for process_id in "${process_ids[@]}"; do
    wait "$process_id" || exit_status=$?
done
exit "$exit_status"
