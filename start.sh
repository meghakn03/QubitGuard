#!/bin/sh
# Start the dashboard, API, simulation worker and persistent database together.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required. Install and start Docker Desktop, then run ./start.sh again." >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose is required. Install Docker Desktop or the Docker Compose plugin." >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop (or Docker Engine), then run ./start.sh again." >&2
    exit 1
fi

docker compose up --build --detach --wait
printf '\nQubitGuard is running at http://localhost:%s\n' "${QUBITGUARD_PORT:-8766}"
printf 'Stop: docker compose down\n'
