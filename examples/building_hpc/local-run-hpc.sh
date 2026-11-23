#!/usr/bin/env bash
# Runs the example with ecosim-hpc on this machine: a local Dask scheduler and workers instead of
# SLURM and MPI. Arguments are passed on to ecosim-hpc, like --steps 10. DASK_WORKERS sets the
# number of workers, 2 by default.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

scheduler_file=scheduler.json
startup_timeout_in_seconds=60
process_ids=()

stop_dask() {
    kill "${process_ids[@]}" 2>/dev/null || true
    wait "${process_ids[@]}" 2>/dev/null || true
    rm -f "$scheduler_file"
}
trap stop_dask EXIT

# the file of an earlier run points at a scheduler that is gone
rm -f "$scheduler_file"
uv run --project .. dask scheduler --scheduler-file "$scheduler_file" > dask-scheduler.log 2>&1 &
process_ids+=("$!")
for _ in $(seq "$startup_timeout_in_seconds"); do
    [ -f "$scheduler_file" ] && break
    sleep 1
done
if [ ! -f "$scheduler_file" ]; then
    echo "The Dask scheduler did not start within $startup_timeout_in_seconds s, see dask-scheduler.log" >&2
    exit 1
fi

uv run --project .. dask worker --scheduler-file "$scheduler_file" --nworkers "${DASK_WORKERS:-2}" > dask-workers.log 2>&1 &
process_ids+=("$!")

uv run --project .. ecosim-hpc --interactive \
    --server-config server/preferences.ini \
    --simulation-config server/simulation.json \
    --simulator-dir modules/ \
    --steps 100 \
    --database-type file \
    "$@"
