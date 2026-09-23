#!/usr/bin/env bash
set -Eeuo pipefail

container_name="${CODEX_CONTAINER_NAME:-airi-symphony-orchestrator-1}"
host_state_root="${SYMPHONY_HOST_STATE_ROOT:-/home/sephy/symphony-airi/symphony-spark-container/state/runtime}"
container_state_root="${SYMPHONY_CONTAINER_STATE_ROOT:-/var/lib/symphony}"

remote_workdir="${PWD:-$host_state_root}"
if [[ "$remote_workdir" == "$host_state_root" || "$remote_workdir" == "$host_state_root/"* ]]; then
  container_workdir="$container_state_root${remote_workdir#"$host_state_root"}"
else
  container_workdir="${CODEX_CONTAINER_WORKDIR:-$container_state_root}"
fi

if ! docker inspect --format '{{.State.Running}}' "$container_name" 2>/dev/null | grep -qx true; then
  echo "The Symphony Codex container is not running: $container_name" >&2
  exit 1
fi

exec docker exec -i --workdir "$container_workdir" "$container_name" /usr/local/bin/codex "$@"
