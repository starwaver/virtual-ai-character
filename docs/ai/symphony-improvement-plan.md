# Symphony improvement plan

Date: 2026-09-22

Status: Accepted.

Issue: #3

## Goal

Give Spark Symphony a bounded task contract with traceable acceptance evidence. Keep the existing model routes and container boundaries.

## Baseline

The repository snapshot already contains a Luna XHigh coordinator, an Astra High planner, Luna and Qwen implementation roles, and an Astra High progress reviewer. The deployment still has one issue slot. The source and installed agent files can drift.

The initial baseline had role files, execution paths, artifact examples, and basic validators. The finalized validators reject contradictory records and accept an explicit workflow path outside the deployment directory.

The first continuation exposed incomplete worker evidence, weak repair ownership, stale review evidence, malformed input crashes, and incomplete drift targets. The current repair pass keeps those records as history and adds executable checks for the remaining evidence gaps. Required checks bind to the reviewed evidence revision and source fingerprint. Repair records inherit exact predecessor scopes. Route records cover every mandatory task. Drift reports include extra target files.

## Accepted design

Use the Spark default route unless a user gives an explicit safe override.

| Role | Route | Rule |
| --- | --- | --- |
| Primary coordinator | `gpt-5.6-luna`, `xhigh` | Keep this route fixed. |
| Planner | `gpt-6-astra`, `high` | Run once before edits. |
| Implementation worker | `gpt-5.6-luna`, `xhigh` | Use by default for bounded work. |
| Qwen implementation worker | `qwen3.8-27b`, `low` | Use only for self-contained bounded work. |
| Progress reviewer | `gpt-6-astra`, `high` | Read-only checkpoint review. |
| Acceptance reviewer | `gpt-6-astra`, `high` | Read-only independent final review. |

An explicit user override can select the light or full path. It can select the implementation route for a bounded task. It cannot remove the planner, acceptance reviewer, required checks, ownership rules, repair limit, or security rules.

## Execution paths

The coordinator records the selected path and its reason in the plan artifact.

The light path uses one planner, one implementation worker, the required checks, and one acceptance review. It uses the progress reviewer only after 15 minutes or a material risk change.

The full path uses one planner and up to three implementation workers in disjoint waves. It uses progress review after the first wave starts, after each wave completes, after 15 minutes of work, and before final validation. It uses the acceptance reviewer after repair and validation finish.

The coordinator does not force parallel work when tasks share files or dependencies.

## Task graph

| Task | Exact files | Dependencies | Route | Completion evidence |
| --- | --- | --- | --- | --- |
| `PLAN-001` | Read-only review of the four sets below | None | Planner, Astra High | The planner returns this graph, the acceptance map, risks, and exact validation commands. |
| `IMPLEMENT-005` | Set A | `PLAN-001` | Implementation worker, Luna XHigh | The contract records exact scope, dependency order, continuation, checkpoint, repair, and review rules. |
| `PROGRESS-003` | Set A | `PLAN-001` | Progress reviewer, Astra High | The first-wave checkpoint returns `CONTINUE`, `REDIRECT`, or `BLOCKED` with evidence. |
| `PROGRESS-004` | Set A | `IMPLEMENT-005`, `PROGRESS-003` | Progress reviewer, Astra High | The contract boundary passes before validator work starts. |
| `IMPLEMENT-006` | Set B | `PROGRESS-004` | Implementation worker, Luna XHigh | The route validator and drift producer agree, and the configuration tests pass. |
| `IMPLEMENT-007` | Set C | `PROGRESS-004` | Coordinator fallback, Luna XHigh | The publication gate rejects the confirmed evidence bypasses, and its tests pass. |
| `PROGRESS-005` | Sets B and C | `IMPLEMENT-006`, `IMPLEMENT-007` | Progress reviewer, Astra High | The validator wave passes its scope, route, and evidence checkpoint. |
| `IMPLEMENT-008` | Set D | `PROGRESS-005` | Coordinator fallback, Luna XHigh | The operating docs match the executable checks and recovery limits. |
| `PROGRESS-006` | Sets A through D | `IMPLEMENT-008` | Progress reviewer, Astra High | The final checkpoint passes before validation. |
| `VALIDATE-001` | Runtime evidence only | `PROGRESS-006` and every implementation or repair task | Coordinator, Luna XHigh | The coordinator records the final checks, diff review, route evidence, and draft handoff. |
| `ACCEPT-001` | Runtime evidence only | `VALIDATE-001` | Acceptance reviewer, Astra High | The independent reviewer returns `ACCEPT` with all six IDs passed. |

Set A owns these exact files: `WORKFLOW.md`, `docs/ai/adr/002-symphony-model-routing.md`, `docs/ai/symphony-improvement-plan.md`, `symphony-spark-container/.dockerignore`, `symphony-spark-container/.env.example`, `symphony-spark-container/.gitignore`, `symphony-spark-container/Dockerfile`, `symphony-spark-container/compose.yaml`, `symphony-spark-container/config/agents/acceptance-reviewer.toml`, `symphony-spark-container/config/agents/implementation-worker-qwen.toml`, `symphony-spark-container/config/agents/implementation-worker.toml`, `symphony-spark-container/config/agents/planner.toml`, `symphony-spark-container/config/agents/progress-orchestrator.toml`, `symphony-spark-container/config/config.toml`, `symphony-spark-container/config/spark-qwen.config.toml`, `symphony-spark-container/github-known-hosts`, `symphony-spark-container/scripts/codex-container-wrapper.sh`, `symphony-spark-container/scripts/issue-labeler.sh`, `symphony-spark-container/scripts/ssh-agent-entrypoint.sh`, and `symphony-spark-container/scripts/symphony-entrypoint.sh`.

Set B owns these exact files: `symphony-spark-container/scripts/check-config.py` and `symphony-spark-container/tests/check-config.test.py`.

Set C owns these exact files: `symphony-spark-container/scripts/check-publication.py` and `symphony-spark-container/tests/check-publication.test.py`.

Set D owns these exact files: `docs/ai/symphony.md`, `docs/ai/adr/003-symphony-task-acceptance.md`, and `symphony-spark-container/README.md`.

Each implementation task excludes every file in the other sets and every path outside the issue scope. It uses literal relative paths. It does not use a file glob or a directory as a changed-file claim. The validator tasks run in one disjoint wave after `IMPLEMENT-005` and the progress checkpoint. The documentation task runs after both validators pass. The coordinator runs no worker concurrently with an overlapping repair.

The full path is selected because the contract crosses role configuration, validation scripts, tests, workflow policy, and operations documentation. Luna owns implementation because the changes cross policy and security boundaries. Astra owns planning, progress review, and acceptance review. Qwen remains configured, but this task does not use it. If an implementation-worker slot is unavailable, Luna records a sequential `coordinator-fallback` task and does not claim a worker invocation.

### Continuation repair wave

The renewed review found stale evidence in the first draft. Keep the first repair record and its source outputs. Do not rename it or reset the repair count.

| Task | Exact files | Dependency | Route | Completion evidence |
| --- | --- | --- | --- | --- |
| `REPAIR-2-001` | `symphony-spark-container/scripts/check-publication.py`, `symphony-spark-container/tests/check-publication.test.py` | `REPAIR-1-001` | Implementation worker, Luna XHigh | New reproductions fail before the fix. The focused suite passes after the fix. |
| `REPAIR-2-002` | `WORKFLOW.md`, `docs/ai/symphony-improvement-plan.md` | `REPAIR-2-001` | Coordinator integration, Luna XHigh | The contract examples, ownership sets, and evidence limits match the gate. |
| `REPAIR-2-003` | `docs/ai/symphony.md`, `docs/ai/adr/003-symphony-task-acceptance.md`, `symphony-spark-container/README.md` | `REPAIR-2-001` | Coordinator integration, Luna XHigh | The operating docs match the final validator and recovery limits. |

The coordinator owns the final documentation integration. It records those edits in the repair evidence. The implementation worker owns only `REPAIR-2-001`. The two documentation scopes do not overlap the worker scope.

## Acceptance IDs

The contract uses these exact IDs:

- `ACC-001`: The task graph has exact ownership, dependencies, a selected path, and observable completion criteria.
- `ACC-002`: Each role has the required model route and a route reason.
- `ACC-003`: Durable status and attempt records support continuation without repeated completed work.
- `ACC-004`: Independent acceptance review and bounded repair tasks cover failed or missing evidence.
- `ACC-005`: Truthful check records and the publication handoff reject incomplete evidence.
- `ACC-006`: Security limits, rollback limits, and source-to-installed drift reporting are defined.

Each ID uses `passed`, `failed`, `blocked`, or `unrun`. `unrun` never means `passed`.

## Durable artifacts

Use these versioned schemas in the issue workspace or Symphony runtime state:

- `symphony.task.v1` stores the plan and each task. It stores task IDs, issue and plan IDs, acceptance IDs, dependencies, exact paths, owner, route, route reason, path, wave, stage, status, attempt, evidence, risks, decisions, repair data, and timestamps.
- `symphony.worker-result.v1` stores one structured result for each implementation attempt. It stores the task identity, attempt, exact changed files, route invocation, output reference, checks, risks, and unfinished work.
- `symphony.checkpoint.v1` stores the progress reviewer, trigger, wave, decision, evidence, and required action.
- `symphony.publication.v1` stores acceptance results, checks, the final review, repairs, drift hashes, Git scope, and publication status.

Runtime evidence stays out of application source commits. A continuation reuses accepted task records and starts only unfinished or repair tasks.

## Status and repair rules

The normal task flow is:

`queued -> planning -> planned -> ready -> running -> review -> accepted -> published`

An attempt can enter `failed` or `blocked`. A failed attempt returns to `ready` only with a new attempt number. A review can enter `repair_required` only with an owned repair task.

The plan allows two repair cycles. Each failed check names one repair task, exact files, an owner, a route, affected acceptance IDs, and rerun commands. A repair task and its record use the exact scope of the direct predecessor. The coordinator reruns affected checks and the acceptance reviewer after repair. A second failed repair blocks publication. No third repair cycle starts.

## Publication evidence

The coordinator first creates a draft `symphony.publication.v1` handoff with task, route, checkpoint, drift, and required-check evidence. The acceptance reviewer reads that draft. The coordinator finalizes it only after all six acceptance IDs pass and the reviewer returns `ACCEPT`. No repair or review finding remains open. The final diff stays in scope.

The route checker validates the complete non-secret source inventory, required role identities, default Luna route, Qwen provider and profile, and the exact Luna primary command. The publication gate validates task dependencies, exact scope paths, correlated worker results, active changed-file ownership, route identity, check commands, exit types, UTC timestamps, check freshness, review freshness, repair records, publication metadata, and both drift targets. A target is matched only when required hashes match and no extra files exist. It requires matched drift hashes only for an approved live rollout.

The coordinator computes the source fingerprint from the reviewed source and changed-file set. The gate compares the declared fingerprint with every check and review record. The gate does not prove that a model used the declared route or that a worker ran the declared command.

The coordinator does not infer success from HTTP `200`, process startup, a healthy container, or a worker claim. The pull request evidence names the actual planner, workers, routes, progress decisions, acceptance verdict, checks, and pull request.

## Drift, security, and rollback

Hash only non-secret source and installed configuration files with SHA-256. Compare `WORKFLOW.md` and seven configuration files with the image copies. Compare the workflow and seven configuration files with the installed mirror. Compare only the seven configuration files with the `$CODEX_HOME` copies. Exclude `.env`, secrets, login state, keys, tokens, cookies, logs, runtime state, and workspaces.

The operator can run the read-only `check-config.py compare` command against the image configuration, the installed mirror, and `$CODEX_HOME`. The report records the complete file inventory and SHA-256 values for both targets. The command reads no credential paths.

The contract is procedural. The Spark front matter, Codex command, container sandbox, issue slot, and installed custom-agent files provide direct runtime controls. The coordinator and the acceptance reviewer provide the publication gate. The role files do not make GitHub or the model server enforce task acceptance.

Keep the current container security, private Qwen network, trusted-author gate, and single issue slot. The issue worker does not alter the live deployment. The desktop coordinator rolls back a bad repository rollout by restoring the last accepted source revision, rebuilding the orchestrator image, and restarting it at an idle point.

## Validation

Run these commands from the repository root:

```bash
python3 -B symphony-spark-container/tests/check-config.test.py -v
python3 -B symphony-spark-container/tests/check-publication.test.py -v
python3 symphony-spark-container/scripts/check-config.py validate \
  --workspace symphony-spark-container \
  --workflow WORKFLOW.md
git diff --check
git diff origin/main --check
bash -n symphony-spark-container/scripts/symphony-entrypoint.sh
pnpm typecheck
pnpm lint
python3 symphony-spark-container/scripts/check-publication.py \
  --artifact .git/symphony/issue-3/publication.json
```

Record each command, its integer exit status, and its result in the publication artifact. Run the publication gate with `python3 symphony-spark-container/scripts/check-publication.py --artifact <publication-artifact>` after the independent reviewer returns `ACCEPT`. Use `--live-rollout` only for an operator-approved rollout with matched drift.

## Files in this change

- `WORKFLOW.md`
- `symphony-spark-container/config/agents/planner.toml`
- `symphony-spark-container/config/agents/implementation-worker.toml`
- `symphony-spark-container/config/agents/implementation-worker-qwen.toml`
- `symphony-spark-container/config/agents/progress-orchestrator.toml`
- `symphony-spark-container/config/agents/acceptance-reviewer.toml`
- `symphony-spark-container/scripts/check-config.py`
- `symphony-spark-container/scripts/check-publication.py`
- `symphony-spark-container/tests/check-config.test.py`
- `symphony-spark-container/tests/check-publication.test.py`
- `symphony-spark-container/scripts/symphony-entrypoint.sh`
- `symphony-spark-container/.gitignore`
- `symphony-spark-container/.dockerignore`
- `symphony-spark-container/README.md`
- `docs/ai/symphony.md`
- `docs/ai/symphony-improvement-plan.md`
- `docs/ai/adr/003-symphony-task-acceptance.md`
