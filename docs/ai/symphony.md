# Symphony operations

Symphony runs as an always-on Docker Compose project on the Spark server. It polls GitHub issues and starts work without a local computer. It uses the Codex CLI with a ChatGPT Plus login. It does not use an OpenAI API key.

Deployment files live in `symphony-spark-container/`. The repository task contract lives in `WORKFLOW.md`.

An issue worker edits only its assigned issue workspace. It does not change the live Spark deployment, model service, container security, or credential files. Only the coordinator and an operator act on the deployment after the publication gate passes.

## Dispatch flow

1. A trusted issue author creates an issue.
2. The labeler adds `symphony` and `symphony-dispatched` within 15 seconds.
3. Symphony creates or reuses an isolated issue workspace.
4. Luna XHigh selects the light or full path and records the reason.
5. Luna XHigh starts one read-only Astra High planner before edits.
6. Luna persists the plan and task records with exact ownership, dependencies, attempts, and acceptance IDs.
7. Luna starts workers only after their dependencies pass.
8. The progress reviewer records full-path wave decisions and any required action.
9. Luna integrates the work and records all required checks.
10. Luna creates a draft publication handoff before the independent Astra acceptance review.
11. Luna creates an owned repair task when the reviewer returns `REPAIR`.
12. Luna reruns affected checks and starts a fresh acceptance review after each repair.
13. Luna runs the publication gate after the reviewer returns `ACCEPT`.
14. Luna publishes through the restricted SSH agent and host-side GitHub tool.
15. Luna removes the `symphony` label. A maintainer reviews and merges the pull request.

Only issues from authors with GitHub `author_association` equal to `OWNER`, `MEMBER`, or `COLLABORATOR` enter the queue. The dispatch marker prevents a finished issue from entering the queue again. An unknown public user cannot start a model run by creating an issue.

## Ownership and routes

The coordinator owns task assignment, integration, evidence, repository checks, Git actions, and publication. Each worker owns only the exact paths in its task record. A worker reports `scope_error` when it needs another path.

| Role | Route | Ownership |
| --- | --- | --- |
| Primary coordinator | `gpt-5.6-luna`, `xhigh` | Integration, validation, Git, and publication |
| Planner | `gpt-6-astra`, `high` | Read-only task graph and route plan |
| Implementation worker | `gpt-5.6-luna`, `xhigh` | Bounded implementation by default |
| Qwen implementation worker | `qwen3.8-27b`, `low` | Self-contained bounded implementation only |
| Progress reviewer | `gpt-6-astra`, `high` | Read-only progress decision |
| Acceptance reviewer | `gpt-6-astra`, `high` | Read-only independent final review |

Every route record includes the role, model, reasoning level, task ID, route reason, invocation ID, status, and observed time. Qwen cannot plan, coordinate, review progress, or accept a task.

## Execution paths

Select a path before the planner starts. Record the path, reason, and any user override in `symphony.task.v1`.

The light path is for one bounded, low-risk task with one owner and no cross-file dependency. It uses one planner, one worker, the required checks, and one independent acceptance review. It uses the progress reviewer only after 15 minutes or a material risk change.

The full path is for cross-cutting, high-risk, or multi-owner work. It uses one planner and up to three workers in disjoint waves. The progress reviewer records decisions after the first wave, after each later wave, after 15 minutes, and before final validation.

Both paths use the same acceptance IDs, artifacts, repair limit, required checks, and publication gate. A light path can omit progress records only when it has no progress checkpoint.

## Durable evidence

Store runtime evidence in the issue workspace or Symphony runtime state. Do not commit runtime logs, reports, credentials, or task artifacts to application source.

- `symphony.task.v1` stores the plan, task graph, ownership, exact scope, route, status, attempt, evidence, risks, and repair data.
- `symphony.worker-result.v1` stores one result for each worker attempt, including changed files, acceptance IDs, route identity, output reference, checks, risks, unfinished work, and scope errors.
- `symphony.checkpoint.v1` stores each progress reviewer decision, worker wave, evidence, and required action.
- `symphony.publication.v1` stores the final tasks, routes, checks, acceptance results, review, repairs, drift, Git scope, and publication status.

Use these task statuses:

`queued -> planning -> planned -> ready -> running -> review -> accepted -> published`

Use `failed`, `blocked`, or `repair_required` only with new evidence and an owned next action. A continuation reuses accepted tasks and starts only unfinished or repair tasks. Never treat missing evidence as a pass.

## Acceptance and repair

The acceptance reviewer records one status for each exact ID: `ACC-001`, `ACC-002`, `ACC-003`, `ACC-004`, `ACC-005`, and `ACC-006`. Each status is `passed`, `failed`, `blocked`, or `unrun`. Only `passed` allows publication.

The reviewer reads the final diff and the draft handoff independently. It returns `ACCEPT`, `REPAIR`, or `BLOCKED`. A repair task names one owner, an exact scope, affected acceptance IDs, and the checks to run again.

Allow at most two repair cycles for one plan. Rerun every affected check and the acceptance review after each repair. A second failed repair blocks publication. Do not start a third repair cycle.

## Required checks and publication

Run these commands from the repository root:

```bash
python3 -B symphony-spark-container/tests/check-config.test.py -v
python3 -B symphony-spark-container/tests/check-publication.test.py -v
python3 symphony-spark-container/scripts/check-config.py validate \
  --workspace symphony-spark-container \
  --workflow WORKFLOW.md
git diff --check
pnpm typecheck
pnpm lint
```

Record each command, integer exit status, status, observed time, and result summary. The publication artifact uses the required check IDs `focused-tests`, `route-check`, `git-diff-check`, `pnpm-typecheck`, and `pnpm-lint`.

Run the publication gate after the acceptance reviewer returns `ACCEPT`:

```bash
python3 symphony-spark-container/scripts/check-publication.py \
  --artifact /path/to/publication.json
```

The gate returns `0` for accepted evidence, `2` for missing, failed, contradictory, or open evidence, and `3` when it cannot read the artifact. It does not create records or infer worker results.

The gate requires one completed worker result for each implementation or repair task. It matches the result to the task attempt, route invocation, exact changed files, and output reference. It rejects a failed result, an unrun result, a stale result, and an unowned changed file.

## Configuration drift

The configuration report reads only the workflow and non-secret configuration allowlist. Run its source report when the deployment and `WORKFLOW.md` use separate roots:

```bash
python3 symphony-spark-container/scripts/check-config.py source \
  --workspace symphony-spark-container \
  --workflow WORKFLOW.md
```

The entrypoint compares the source copies with its installed mirror and `$CODEX_HOME` copies. It records file names, sizes, modes, and SHA-256 values without printing file contents. The compare report can be generated inside the orchestrator with:

```bash
docker compose exec --no-TTY orchestrator \
  python3 /usr/local/lib/symphony/check-config.py compare \
  --workspace /opt/symphony \
  --workflow /opt/symphony/WORKFLOW.md \
  --installed-root /var/lib/symphony/install \
  --codex-home /var/lib/symphony/codex
```

Compare `WORKFLOW.md`, `config/config.toml`, all five agent TOMLs, and `config/spark-qwen.config.toml`. Compare both the installed mirror and `$CODEX_HOME`. Exclude `.env`, `secrets/`, `auth.json`, keys, tokens, cookies, logs, runtime state, and workspaces. A `mismatch` or `unavailable` result blocks a live rollout.

## Qwen profile and capacity

Spark also provides an explicit local Qwen profile. The `qwen-init` container downloads `Qwen/Qwen3.8-27B`. The `qwen` service runs the model in a vLLM container. The service has no host port. The orchestrator reaches it through the private Compose network at `http://qwen:8000/v1`.

The profile does not replace the required Astra and Luna routes. The planner selects Qwen only for bounded implementation work that fits the local model. The model container has a 64 GiB memory limit and the `owner: sephy` label.

The Codex session allows four concurrent subagent threads. A normal worker wave uses up to three implementation workers and one progress reviewer. The deployment still runs one GitHub issue at a time because `agent.max_concurrent_agents` remains `1`.

Codex loads the routes from deployment-owned custom-agent files. The Symphony parent process also pins the main session to Luna XHigh.

## Authentication

The deployment has three separate credential boundaries:

- The Codex state directory contains the ChatGPT Plus login created by `codex login --device-auth`.
- Symphony holds the GitHub token and exposes GitHub requests to Codex through the `github_api` tool. It removes the raw token from the Codex child environment.
- A separate container holds the write-enabled GitHub deploy key. Codex receives only its Unix socket, not the key file.

Docker is the process sandbox for Codex. The orchestrator has a read-only root filesystem, no Linux capabilities, no privilege escalation, one persistent runtime volume, and one loopback-only dashboard port. Codex uses `externalSandbox` mode because its inner Linux sandbox cannot create namespaces inside this hardened container.

Treat `auth.json`, `.env`, and the deploy key as passwords. They are ignored by Git and remain on Spark.

OpenAI documents ChatGPT-managed authentication for a persistent trusted runner as an advanced option. The CLI refreshes the saved login. Keep one auth copy on one machine and serialize work because concurrent refreshes from copied credentials can invalidate each other.

## Operations

Use the commands in `symphony-spark-container/README.md` to start, inspect, update, or reauthenticate the stack. The dashboard binds only to `127.0.0.1:4100` on Spark. Use an SSH tunnel to reach it.

The stack does not change or stop the existing Codex containers on Spark.

## Evidence checks

The coordinator keeps local records in the issue workspace or Symphony runtime state. Use `.git/symphony/<issue-id>/` only when the deployment does not provide a runtime state path. Do not commit these records, logs, credentials, or reports to application source.

The publication gate checks evidence shape and consistency. It cannot prove that a worker ran a command or used a route. The coordinator records observed worker output, command output references, and reviewer decisions separately.
