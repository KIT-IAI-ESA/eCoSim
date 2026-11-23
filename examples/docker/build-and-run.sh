#!/usr/bin/env bash
# Builds the images and runs the docker example. The first argument chooses the variant, 'file' (default)
# or 'postgres'. Further arguments are passed on to 'compose up'. ECOSIM_DB_IMAGE sets another database
# image for the postgres variant, see docs/content/guides/docker.md.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

variant="${1:-file}"
if [ "$variant" != file ] && [ "$variant" != postgres ]; then
    echo "Usage: $0 [file|postgres] [compose up options]" >&2
    exit 2
fi
shift $(( $# > 0 ? 1 : 0 ))

tool=$(command -v docker || command -v podman || true)
if [ -z "$tool" ]; then
    echo "Neither docker nor podman is on PATH" >&2
    exit 1
fi

python3 ../../dev/build_docker_images.py ecosim-server ecosim-client-fmu-v2

stop_example() {
    "$tool" compose --file "$variant/compose.yaml" down
}
trap stop_example EXIT

"$tool" compose --file "$variant/compose.yaml" up --abort-on-container-exit --exit-code-from server "$@"
