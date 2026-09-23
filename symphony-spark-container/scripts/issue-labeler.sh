#!/usr/bin/env bash
set -Eeuo pipefail

github_api_url="${GITHUB_API_URL:-https://api.github.com}"
github_repository="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
poll_seconds="${ISSUE_POLL_SECONDS:-15}"
required_label="${SYMPHONY_REQUIRED_LABEL:-symphony}"
dispatch_marker="${SYMPHONY_DISPATCH_MARKER:-symphony-dispatched}"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is required." >&2
  exit 1
fi

if ! [[ "$poll_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "ISSUE_POLL_SECONDS must be a positive integer." >&2
  exit 1
fi

github_request() {
  curl \
    --fail-with-body \
    --silent \
    --show-error \
    --header "Accept: application/vnd.github+json" \
    --header "Authorization: Bearer $GITHUB_TOKEN" \
    --header "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

while true; do
  if issues_json="$(github_request "$github_api_url/repos/$github_repository/issues?state=open&sort=created&direction=desc&per_page=100")"; then
    while IFS= read -r issue_number; do
      label_payload="$(
        jq \
          --null-input \
          --compact-output \
          --arg required_label_name "$required_label" \
          --arg dispatch_marker_name "$dispatch_marker" \
          '{labels: [$required_label_name, $dispatch_marker_name]}'
      )"

      if github_request \
        --request POST \
        --header "Content-Type: application/json" \
        --data "$label_payload" \
        "$github_api_url/repos/$github_repository/issues/$issue_number/labels" >/dev/null; then
        printf 'Queued trusted issue #%s with labels %s and %s.\n' \
          "$issue_number" \
          "$required_label" \
          "$dispatch_marker"
      fi
    done < <(
      jq --raw-output --arg dispatch_marker_name "$dispatch_marker" '
        .[]
        | select(has("pull_request") | not)
        | select(
            .author_association == "OWNER"
            or .author_association == "MEMBER"
            or .author_association == "COLLABORATOR"
          )
        | select(([.labels[].name] | index($dispatch_marker_name)) == null)
        | .number
      ' <<<"$issues_json"
    )
  else
    echo "GitHub issue polling failed. The labeler will retry." >&2
  fi

  sleep "$poll_seconds"
done
