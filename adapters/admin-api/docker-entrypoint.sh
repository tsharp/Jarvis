#!/bin/sh
set -eu

APP_UID="${TRION_CONTAINER_UID:-1000}"
APP_GID="${TRION_CONTAINER_GID:-1000}"
APP_DATA_DIR="${COMMANDER_DATA_DIR:-/app/data}"
STORAGE_BROKER_DIR="$(dirname "${STORAGE_BROKER_SETTINGS_PATH:-/app/storage_broker/storage_policy.json}")"
TRION_HOME_DIR="${TRION_HOME_DIR:-/trion-home}"
MEMORY_DATA_DIR="${MEMORY_DATA_DIR:-/app/memory_data}"
PROTOCOL_DIR="${PROTOCOL_DIR:-/app/memory}"
MEMORY_SPEICHER_DIR="${MEMORY_SPEICHER_DIR:-/app/memory_speicher}"
HOME_DIR="${ADMIN_API_HOME:-${APP_DATA_DIR}/home}"

prepare_writable_dir() {
  dir="$1"
  mkdir -p "$dir"
  chown -R "${APP_UID}:${APP_GID}" "$dir"
  chmod u+rwX,g+rwX "$dir"
}

append_group() {
  group_id="$1"
  [ -n "$group_id" ] || return 0
  case ",${SET_PRIV_GROUPS}," in
    *,"${group_id}",*) ;;
    *) SET_PRIV_GROUPS="${SET_PRIV_GROUPS},${group_id}" ;;
  esac
}

if [ "$(id -u)" = "0" ]; then
  prepare_writable_dir "$APP_DATA_DIR"
  prepare_writable_dir "$STORAGE_BROKER_DIR"
  prepare_writable_dir "$TRION_HOME_DIR"
  prepare_writable_dir "$MEMORY_DATA_DIR"
  prepare_writable_dir "$PROTOCOL_DIR"
  prepare_writable_dir "$MEMORY_SPEICHER_DIR"
  prepare_writable_dir "$HOME_DIR"

  export HOME="$HOME_DIR"
  export XDG_DATA_HOME="${HOME_DIR}/.local/share"
  export XDG_CACHE_HOME="${HOME_DIR}/.cache"

  SET_PRIV_GROUPS="${APP_GID}"
  DOCKER_SOCK_GID="$(stat -c "%g" /var/run/docker.sock 2>/dev/null || true)"
  append_group "$DOCKER_SOCK_GID"
  append_group "${TRION_DOCKER_GID:-}"

  exec setpriv \
    --reuid="${APP_UID}" \
    --regid="${APP_GID}" \
    --groups="${SET_PRIV_GROUPS}" \
    -- "$@"
fi

exec "$@"
