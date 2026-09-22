# Symphony on Spark

This Compose project runs the official Symphony release on the always-on Spark server. It uses the Codex CLI with a ChatGPT Plus login. It does not use an OpenAI API key.

The stack also runs Qwen3.8-27B in an internal vLLM container. The model is available to bounded implementation subagents through the `spark_qwen` provider. The planner selects Qwen when the task fits that model. The normal Symphony route remains Astra for planning and Luna for primary coordination.

## Services

| Service | Purpose | Secret access |
| --- | --- | --- |
| `orchestrator` | Poll issues, create isolated workspaces, and run Codex | ChatGPT login and a forwarded SSH-agent socket |
| `issue-labeler` | Add `symphony` to new trusted-author issues | GitHub token |
| `ssh-agent` | Hold the repository deploy key and approve Git pushes | GitHub deploy key |
| `qwen-init` | Download Qwen3.8-27B into a Docker volume | Public model weights only |
| `qwen` | Serve Qwen3.8-27B through an internal vLLM API | Persistent model volume |

Symphony removes the GitHub token from the Codex child process. The orchestrator does not mount the deploy-key file. It can use only the SSH-agent socket.

Docker is the process sandbox. The container has a read-only root filesystem, no Linux capabilities, and no privilege escalation. Codex uses app-server `externalSandbox` mode because its inner Linux sandbox needs namespace permissions that this container does not grant. The official Symphony binary also needs an executable temporary filesystem to start its bundled runtime. That filesystem remains temporary, `nosuid`, and `nodev`.

## Model routing

| Work | Model | Reasoning |
| --- | --- | --- |
| Planning | `gpt-6-astra` | `high` |
| Primary coordination and final validation | `gpt-5.6-luna` | `xhigh` |
| Bounded implementation worker | `gpt-5.6-luna` | `xhigh` |
| Bounded implementation worker selected by the planner | `qwen3.8-27b` | `low` |
| Progress review | `gpt-6-astra` | `high` |
| Acceptance review | `gpt-6-astra` | `high` |

Qwen is an explicit local profile. Run it inside the orchestrator container when you need the local model:

```bash
docker compose exec orchestrator codex --profile spark-qwen
```

The Qwen API has no published host port. The orchestrator reaches it at `http://qwen:8000/v1` on the private `airi-symphony-model` network. The model container has a 64 GiB RAM limit, no swap allowance, twelve CPUs, one request sequence, and the `owner: sephy` label.

The service uses `Qwen/Qwen3.8-27B` with a 65,536-token context limit. It enables the Qwen reasoning parser and vLLM automatic tool calling. The image digest is pinned in `compose.yaml`.

The Luna coordinator must start the custom Astra planner before it edits files. After planning, it can run up to three workers in parallel when their file ownership does not overlap. It must run the read-only `progress-orchestrator` after each worker wave and before final validation. It must create a draft handoff, run the independent Astra acceptance reviewer, and run the publication gate before it publishes a pull request. The Codex session cap is four concurrent subagent threads, so one review can run with three workers. The planner selects either the Luna or Qwen implementation role for each worker.

Each worker edits only the exact paths in its task record. The coordinator owns the plan, task records, integration, checks, Git actions, and publication. The worker returns one `symphony.worker-result.v1` object for each attempt. The gate matches that result to the task attempt, route invocation, output reference, and changed files. A scope error, stale attempt, failed check, or missing evidence does not count as completion.

The light path uses one planner, one worker, the required checks, and one independent acceptance review. The full path uses up to three workers in disjoint waves and progress checkpoints. Both paths use the same six acceptance IDs, durable artifacts, two-cycle repair limit, and publication gate.

Store `symphony.task.v1`, `symphony.worker-result.v1`, `symphony.checkpoint.v1`, and `symphony.publication.v1` records in issue or runtime state. Do not commit runtime records, logs, reports, or credentials to application source.

Validate the required role routes before a rollout:

```bash
python3 scripts/check-config.py validate --workspace . --workflow ../WORKFLOW.md
```

Run the publication gate against the coordinator handoff artifact:

```bash
python3 scripts/check-publication.py --artifact /path/to/publication.json
```

The gate rejects missing, failed, or contradictory evidence. Add `--live-rollout` only when the operator has a matched drift report.

The gate accepts a light-path handoff without a progress route. It requires a progress route and checkpoint records for a full-path handoff. Both paths require the same acceptance IDs, required checks, independent acceptance review, and repair limit.

Run the focused validation and repository checks from the repository root:

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

Record the integer exit status for every command. The publication artifact uses `focused-tests`, `route-check`, `git-diff-check`, `pnpm-typecheck`, and `pnpm-lint`.

The source layout keeps `WORKFLOW.md` above this deployment directory. Report that layout with:

```bash
python3 scripts/check-config.py source \
  --workspace . \
  --workflow ../WORKFLOW.md
```

The source report contains file names, sizes, modes, and SHA-256 values. It does not print file contents. The compare command uses the same `--workflow` option when the source and workflow files use separate roots.

The orchestrator runs the compare command against its image configuration, installed mirror, and `$CODEX_HOME` copies:

```bash
docker compose exec --no-TTY orchestrator \
  python3 /usr/local/lib/symphony/check-config.py compare \
  --workspace /opt/symphony \
  --workflow /opt/symphony/WORKFLOW.md \
  --installed-root /var/lib/symphony/install \
  --codex-home /var/lib/symphony/codex
```

The compare result is `matched`, `mismatch`, or `unavailable`. A mismatch or unavailable result blocks a live rollout. The report reads only `WORKFLOW.md`, `config/config.toml`, all five agent TOML files, and `config/spark-qwen.config.toml`. It compares the installed mirror and the `$CODEX_HOME` files. It reads no credential paths.

## No live deployment from an issue task

Issue workers do not run deployment commands or change the live Spark files. They do not change model-serving files, credentials, container security, or another workspace. The coordinator publishes only after the independent acceptance reviewer returns `ACCEPT` and the publication gate returns exit status `0`.

Use `--live-rollout` only when an operator approves a live rollout and the drift record has status `matched`. A repository task does not deploy Spark. An operator applies a reviewed update at an idle point.

## One-time setup

Run these commands from the deployment directory on Spark:

```bash
install -d -m 0700 secrets state/codex state/runtime state/ssh-agent
ssh-keygen -t ed25519 -N '' -C 'airi-symphony@spark' -f secrets/github-deploy-key
chmod 0600 .env secrets/github-deploy-key
docker compose build
docker compose run --rm --entrypoint codex orchestrator login --device-auth
docker compose up --detach
```

The first start downloads the Qwen weights into a persistent Docker volume. The download runs inside the `qwen-init` container. The `qwen` container has no external network route after the download completes.

Add `secrets/github-deploy-key.pub` to `starwaver/virtual-ai-character` as a write-enabled deploy key before starting the services. Put a GitHub token in `.env` as `GITHUB_TOKEN`. The token needs read and write access to repository contents, issues, pull requests, and labels. Create the `symphony` and `symphony-dispatched` repository labels before starting the services.

Treat `state/codex/auth.json` like a password. It contains the renewable ChatGPT login used by the CLI. Keep one login copy on this server. Symphony serializes issue runs through the single configured issue slot, while one issue can use several disjoint subagent threads.

## Operations

Check the stack:

```bash
docker compose ps
docker compose logs --tail 100 orchestrator issue-labeler
curl --fail http://127.0.0.1:4100/api/v1/state
```

Open the dashboard from another computer through an SSH tunnel:

```bash
ssh -L 4100:127.0.0.1:4100 spark
```

Then open `http://127.0.0.1:4100`.

Pull a workflow update from this repository, copy the updated deployment files to Spark, and run:

```bash
docker compose up --detach --build
```

Run this deployment update as an operator after publication. Do not run it from an issue worker.

To update only the Qwen service after a model or vLLM change, run:

```bash
docker compose up --detach qwen
```

To stop the local model without stopping Symphony, run:

```bash
docker compose stop qwen
```

## Issue dispatch

The labeler polls the 100 newest open issues every 15 seconds. It queues an issue only when GitHub reports the author as `OWNER`, `MEMBER`, or `COLLABORATOR`. It adds `symphony` and the durable `symphony-dispatched` marker together. This prevents an unknown public user from starting a Plus-backed model run and prevents a finished issue from entering the queue again.

Symphony removes the `symphony` label after it publishes a pull request or records a blocker. It leaves `symphony-dispatched` in place. Restore `symphony` to retry an issue after you fix the blocker.

## Recovery

If the ChatGPT login expires, stop the orchestrator and repeat the device login:

```bash
docker compose stop orchestrator
docker compose run --rm --entrypoint codex orchestrator login --device-auth
docker compose up --detach orchestrator
```

Do not copy `auth.json` to another machine or run concurrent jobs from a copied login.
