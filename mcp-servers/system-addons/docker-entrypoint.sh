#!/bin/sh
set -eu

APP_UID="${TRION_CONTAINER_UID:-1000}"
APP_GID="${TRION_CONTAINER_GID:-1000}"
DATA_DIR="${SYSTEM_ADDONS_DATA_DIR:-/app/data}"
DB_DIR="$(dirname "${SQL_MEMORY_DB_PATH:-${DATA_DIR}/memory.db}")"

prepare_writable_dir() {
  dir="$1"
  mkdir -p "$dir"
  chown -R "${APP_UID}:${APP_GID}" "$dir"
  chmod u+rwX,g+rwX "$dir"
}

if [ "$(id -u)" = "0" ]; then
  prepare_writable_dir "$DATA_DIR"
  prepare_writable_dir "$DB_DIR"
  exec setpriv \
    --reuid="${APP_UID}" \
    --regid="${APP_GID}" \
    --groups="${APP_GID}" \
    -- "$@"
fi

exec "$@"
