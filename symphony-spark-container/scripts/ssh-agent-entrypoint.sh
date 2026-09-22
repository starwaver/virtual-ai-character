#!/usr/bin/env bash
set -Eeuo pipefail

deploy_key_path="${DEPLOY_KEY_PATH:-/run/secrets/github-deploy-key}"

if [[ ! -r "$deploy_key_path" ]]; then
  echo "The GitHub deploy key is not readable: $deploy_key_path" >&2
  exit 1
fi

install -d -m 0700 "$(dirname "$SSH_AUTH_SOCK")"
rm -f "$SSH_AUTH_SOCK"

eval "$(ssh-agent -a "$SSH_AUTH_SOCK" -s)" >/dev/null

cleanup() {
  ssh-agent -k >/dev/null 2>&1 || true
  rm -f "$SSH_AUTH_SOCK"
}
trap cleanup EXIT INT TERM

ssh-add "$deploy_key_path" >/dev/null
ssh-add -l

while kill -0 "$SSH_AGENT_PID" >/dev/null 2>&1; do
  sleep 30
done
