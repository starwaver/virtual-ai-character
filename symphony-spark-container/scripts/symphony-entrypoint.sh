#!/usr/bin/env bash
set -Eeuo pipefail

workflow_path="${SYMPHONY_WORKFLOW_PATH:-/opt/symphony/WORKFLOW.md}"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is required." >&2
  exit 1
fi

if [[ ! -r "$workflow_path" ]]; then
  echo "The Symphony workflow is not readable: $workflow_path" >&2
  exit 1
fi

config_install_dir="${SYMPHONY_INSTALL_DIR:-/var/lib/symphony/install}"
config_report_path="${SYMPHONY_CONFIG_REPORT_PATH:-$SYMPHONY_LOGS_ROOT/config-drift.json}"

compare_config() {
  python3 /usr/local/lib/symphony/check-config.py compare \
    --workspace /opt/symphony \
    --workflow "$workflow_path" \
    --installed-root "$config_install_dir" \
    --codex-home "$CODEX_HOME" \
    --report "$config_report_path"
}

# Preserve an existing target long enough to detect drift before synchronization.
if [[ -e "$config_install_dir/WORKFLOW.md" || -e "$CODEX_HOME/config.toml" ]]; then
  if ! compare_config; then
    echo "Symphony configuration drift check failed. Read the safe report: $config_report_path" >&2
    exit 1
  fi
fi

install -d -m 0700 "$CODEX_HOME" "$CODEX_HOME/agents"
install -m 0600 /opt/symphony/config/config.toml "$CODEX_HOME/config.toml"
install -m 0600 /opt/symphony/config/agents/*.toml "$CODEX_HOME/agents/"
for profile_path in /opt/symphony/config/*.config.toml; do
  if [[ -f "$profile_path" ]]; then
    install -m 0600 "$profile_path" "$CODEX_HOME/$(basename "$profile_path")"
  fi
done
install -d -m 0700 "$HOME" "$SYMPHONY_LOGS_ROOT" "$SYMPHONY_WORKSPACE_ROOT" "$XDG_CACHE_HOME"

install -d -m 0700 "$config_install_dir" "$config_install_dir/config" "$config_install_dir/config/agents"
install -m 0600 "$workflow_path" "$config_install_dir/WORKFLOW.md"
install -m 0600 /opt/symphony/config/config.toml "$config_install_dir/config/config.toml"
for agent_path in /opt/symphony/config/agents/*.toml; do
  install -m 0600 "$agent_path" "$config_install_dir/config/agents/"
done
for profile_path in /opt/symphony/config/*.config.toml; do
  if [[ -f "$profile_path" ]]; then
    install -m 0600 "$profile_path" "$config_install_dir/config/"
  fi
done

if ! compare_config; then
  echo "Symphony configuration drift check failed. Read the safe report: $config_report_path" >&2
  exit 1
fi

if ! codex login status >/dev/null 2>&1; then
  echo "Codex is not logged in. Run the documented device-login command before starting Symphony." >&2
  exit 1
fi

if [[ ! -S "${SSH_AUTH_SOCK:-}" ]] || ! ssh-add -l >/dev/null 2>&1; then
  echo "The GitHub deploy-key agent is not ready." >&2
  exit 1
fi

exec symphony \
  --i-understand-that-this-will-be-running-without-the-usual-guardrails \
  --logs-root "$SYMPHONY_LOGS_ROOT" \
  --port 4000 \
  "$workflow_path"
