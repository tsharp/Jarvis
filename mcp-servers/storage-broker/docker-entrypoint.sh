#!/bin/sh
set -eu

APP_UID="${TRION_CONTAINER_UID:-1000}"
APP_GID="${TRION_CONTAINER_GID:-1000}"
DATA_DIR="${STORAGE_BROKER_DATA_DIR:-/app/data}"
DB_DIR="$(dirname "${STORAGE_BROKER_DB:-${DATA_DIR}/storage_broker.db}")"
POLICY_DIR="$(dirname "${STORAGE_POLICY_PATH:-${DATA_DIR}/storage_policy.json}")"
HOME_DIR="${STORAGE_BROKER_HOME:-${DATA_DIR}/home}"

prepare_writable_dir() {
  dir="$1"
  mkdir -p "$dir"
  chown -R "${APP_UID}:${APP_GID}" "$dir"
  chmod u+rwX,g+rwX "$dir"
}

if [ "$(id -u)" = "0" ]; then
  prepare_writable_dir "$DATA_DIR"
  prepare_writable_dir "$DB_DIR"
  prepare_writable_dir "$POLICY_DIR"
  prepare_writable_dir "$HOME_DIR"
  export HOME="$HOME_DIR"
  export XDG_DATA_HOME="${HOME_DIR}/.local/share"
  export XDG_CACHE_HOME="${HOME_DIR}/.cache"
  exec setpriv \
    --reuid="${APP_UID}" \
    --regid="${APP_GID}" \
    --groups="${APP_GID},6" \
    -- "$@"
fi

exec "$@"
