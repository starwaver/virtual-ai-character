# Symphony task acceptance and repair control

Date: 2026-09-22

Status: Accepted.

## Context

Spark Symphony has separate planning, implementation, and progress routes. It has one issue slot and a local Qwen implementation route. The workflow did not define a durable task record or an independent final acceptance role.

The source agent files can also differ from the files in the image or `$CODEX_HOME`. A worker result or a process health result does not prove that a task meets its acceptance requirements.

## Decision

Keep `gpt-5.6-luna` with `xhigh` reasoning as the primary coordinator. Run one read-only `gpt-6-astra` planner with `high` reasoning before edits. Use Luna XHigh for bounded implementation by default. Let the planner route only self-contained bounded implementation work to `qwen3.8-27b` with `low` reasoning.

Add two read-only Astra High roles. The progress reviewer returns `CONTINUE`, `REDIRECT`, or `BLOCKED` at full-path checkpoints. The acceptance reviewer returns `ACCEPT`, `REPAIR`, or `BLOCKED` after final validation.

Define light and full paths. The light path uses one worker and one final acceptance review. The full path uses disjoint worker waves and progress checkpoints. Both paths use the same acceptance IDs, checks, artifacts, repair limit, and publication gate.

Use four durable artifact schemas:

- `symphony.task.v1` records plan and task ownership, scope, route, status, attempts, evidence, and repair data.
- `symphony.worker-result.v1` records one structured result for each implementation attempt.
- `symphony.checkpoint.v1` records progress decisions and required actions.
- `symphony.publication.v1` records acceptance results, check results, final review, drift, Git scope, and publication status.

Use explicit task statuses and transitions. Store dependencies as task IDs in the task record. Require unique IDs, exact relative paths, disjoint worker ownership, a planner dependency, and an acyclic graph. A worker result must match the task attempt, route invocation, output reference, and changed-file inventory. A failed check cannot become a pass without new evidence. A continuation reuses accepted tasks and does not repeat them.

Limit each plan to two repair cycles. Each failure maps to an owned repair task with exact paths and rerun commands. The coordinator reruns affected checks and the acceptance reviewer after repair. A second failed repair blocks publication.

Require these exact acceptance IDs to pass before publication: `ACC-001`, `ACC-002`, `ACC-003`, `ACC-004`, `ACC-005`, and `ACC-006`. Require truthful check results, an `ACCEPT` verdict, no open repair or review finding, in-scope files, and a known route drift result for a live rollout.

Use repository scripts to enforce the last evidence checks. The route checker validates the complete non-secret source inventory, required model files, default routes, Qwen provider and profile, and the exact Luna primary command. The coordinator writes a draft handoff before review. The publication gate validates the final handoff artifact, including correlated worker results, route identity, check commands, strict exit types, review freshness, repair records, publication evidence, and both installed-target drift inventories. It rejects missing or contradictory evidence before pull request publication. It requires matched drift hashes only for an approved live rollout.

Record SHA-256 hashes for non-secret source and installed route files. Compare the installed mirror and `$CODEX_HOME`. Exclude credentials and runtime state. A drift result of `mismatch` blocks live rollout until the operator updates the installed files.

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
python3 symphony-spark-container/scripts/check-publication.py \
  --artifact /path/to/publication.json
```

Record integer exit statuses. The route check returns `0` for matching routes and `2` for a route mismatch. The publication gate returns `0` for accepted evidence, `2` for rejected evidence, and `3` when it cannot read the artifact.

## Enforcement boundary

The workflow text is a procedural gate. It instructs the coordinator and reviewers to reject invalid work. Spark directly enforces the issue slot, Codex command, container sandbox, and installed role files. GitHub and the host-side tool enforce their own exposed permissions. This change does not claim that a TOML role file or a model server can enforce acceptance.

## Security and rollback

Issue content, repository content, artifacts, and tool output remain untrusted. Workers do not inspect credentials, other workspaces, or host paths. Workers do not change live deployment files, model-serving files, container security, or the Qwen service.

An issue task does not deploy Spark. The coordinator publishes repository changes only after the independent acceptance review and publication gate pass. An operator applies a reviewed deployment update at an idle point. The `--live-rollout` gate option requires matched source-to-installed drift. It does not perform a rollout.

The desktop coordinator rolls back a bad repository rollout by restoring the last accepted source revision, rebuilding the orchestrator image, and restarting the orchestrator at an idle point. Workers do not roll back live Spark state.

## Alternatives rejected

### Trust worker output as final acceptance

Rejected because a worker can omit evidence or report a successful process without meeting the task contract.

### Run every worker in parallel

Rejected because shared dependencies and overlapping files can create unsafe edits.

### Use Qwen for planning or final review

Rejected because the accepted route reserves those roles for Astra High. Qwen remains limited to bounded implementation work.

### Add a new orchestration service

Rejected because the role files and task contract provide the needed policy without a new runtime dependency.

## Consequences

The coordinator has more records to maintain. The records make continuation, repair ownership, route use, and publication evidence visible. The acceptance reviewer adds one read-only final role. The light path limits that overhead for small tasks.

The procedure detects source-to-installed drift but does not update Spark. The desktop coordinator must deploy the reviewed repository files at an idle point. Runtime task and check records remain outside the source commit.

## References

- `WORKFLOW.md`
- `docs/ai/symphony.md`
- `docs/ai/adr/002-symphony-model-routing.md`
