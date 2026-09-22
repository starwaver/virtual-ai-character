# Symphony improvement plan

Date: 2026-09-22

Status: Accepted.

Issue: #3

## Goal

Give Spark Symphony a bounded task contract with traceable acceptance evidence. Keep the existing model routes and container boundaries.

## Baseline

The repository snapshot already contains a Luna XHigh coordinator, an Astra High planner, Luna and Qwen implementation roles, and an Astra High progress reviewer. The deployment still has one issue slot. The source and installed agent files can drift.

The initial baseline had role files, execution paths, artifact examples, and basic validators. The finalized validators reject contradictory records and accept an explicit workflow path outside the deployment directory.

The first continuation exposed incomplete worker evidence, weak repair ownership, stale review evidence, malformed input crashes, and incomplete drift targets. This revision closes those gaps with executable checks and regression cases.

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

| Task | Files | Dependency | Route | Completion evidence |
| --- | --- | --- | --- | --- |
| `REPAIR-002-001` | `WORKFLOW.md`, the five custom-agent TOMLs | Reconciled continuation plan | `implementation-worker`, Luna XHigh | The contract defines result correlation, graph ownership, repair order, review independence, and evidence rules. |
| `REPAIR-002-002` | `symphony-spark-container/scripts/check-config.py`, `symphony-spark-container/tests/check-config.test.py`, `symphony-spark-container/scripts/symphony-entrypoint.sh` | `REPAIR-002-001` | `implementation-worker`, Luna XHigh | The source inventory, safe paths, route fields, Qwen profile, and two target drift report pass. |
| `REPAIR-002-003` | `symphony-spark-container/scripts/check-publication.py`, `symphony-spark-container/tests/check-publication.test.py` | `REPAIR-002-001` | `implementation-worker`, Luna XHigh | Worker results, ownership, repairs, review freshness, malformed input, and complete evidence checks pass. |
| `REPAIR-002-004` | `docs/ai/symphony.md`, `docs/ai/symphony-improvement-plan.md`, `docs/ai/adr/002-symphony-model-routing.md`, `docs/ai/adr/003-symphony-task-acceptance.md`, `symphony-spark-container/README.md` | `REPAIR-002-002`, `REPAIR-002-003` | `implementation-worker`, Luna XHigh | Operating docs, schemas, commands, enforcement limits, and rollback steps match the scripts. |
| `VALIDATE-002` | Runtime evidence only | `REPAIR-002-004` | Primary coordinator, Luna XHigh | Required checks, complete diff review, and the draft handoff are recorded. |
| `ACCEPT-001` | Runtime records only | `VALIDATE-002` | `acceptance-reviewer`, Astra High | An independent review returns `ACCEPT` with all six acceptance IDs passed. |

The full path is selected because the contract crosses role configuration, validation scripts, tests, workflow policy, and operations records. The two validator repairs have disjoint source ownership and can run in one wave after the contract repair. Luna owns each implementation task because the changes cross policy and security boundaries. Astra owns planning and acceptance. Qwen remains configured but this task does not use it.

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

The plan allows two repair cycles. Each failed check names one repair task, exact files, an owner, a route, affected acceptance IDs, and rerun commands. The coordinator reruns affected checks and the acceptance reviewer after repair. A second failed repair blocks publication. No third repair cycle starts.

## Publication evidence

The coordinator first creates a draft `symphony.publication.v1` handoff with task, route, checkpoint, drift, and required-check evidence. The acceptance reviewer reads that draft. The coordinator finalizes it only after all six acceptance IDs pass and the reviewer returns `ACCEPT`. No repair or review finding remains open. The final diff stays in scope.

The route checker validates the complete non-secret source inventory, required role identities, default Luna route, Qwen provider and profile, and the exact Luna primary command. The publication gate validates task dependencies, exact scope paths, correlated worker results, route identity, check commands, exit types, review freshness, repair records, publication evidence, and both drift targets. It requires matched drift hashes only for an approved live rollout.

The coordinator does not infer success from HTTP `200`, process startup, a healthy container, or a worker claim. The pull request evidence names the actual planner, workers, routes, progress decisions, acceptance verdict, checks, and pull request.

## Drift, security, and rollback

Hash only non-secret source and installed configuration files with SHA-256. Compare `WORKFLOW.md`, `config.toml`, agent TOMLs, and profile TOMLs with the image copies and the `$CODEX_HOME` copies. Exclude `.env`, secrets, login state, keys, tokens, cookies, logs, runtime state, and workspaces.

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
pnpm typecheck
pnpm lint
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
