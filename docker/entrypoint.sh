#!/bin/sh
set -eu

# Allow one-off commands, e.g. `docker compose run --rm app python -m app.cli hash-password`
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

DATA_DIR="${DATA_DIR:-/data}"
if ! touch "$DATA_DIR/.write-test" 2>/dev/null; then
  echo "ERROR: $DATA_DIR is not writable by uid $(id -u)." >&2
  echo "Create the host folder yourself (mkdir data) or set PUID/PGID in .env to its owner." >&2
  exit 1
fi
rm -f "$DATA_DIR/.write-test"

alembic upgrade head

ACCESS_LOG="--no-access-log"
if [ "${LOG_ACCESS:-false}" = "true" ]; then
  ACCESS_LOG="--access-log"
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  $ACCESS_LOG
