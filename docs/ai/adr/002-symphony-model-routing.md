# Persistent Spark Symphony with task-based model routing

Date: 2026-09-20

Status: Accepted.

## Decision

Run the official Symphony release in a dedicated Docker Compose project on the always-on Spark server. Use GitHub Issues as the tracker and a repository-owned `WORKFLOW.md` as the task contract.

Use Codex CLI `0.155.1` with a ChatGPT Plus device login stored only on Spark. Pin the main implementation session to `gpt-5.6-luna` with `xhigh` reasoning. Require it to start one custom `planner` agent on `gpt-6-astra` with `high` reasoning before editing. After planning, allow up to three bounded implementation workers in parallel when their file ownership does not overlap. Add a read-only `progress-orchestrator` agent on `gpt-6-astra` with `high` reasoning for worker-wave checkpoints. Let the planner select either the Luna XHigh worker or the local Qwen worker for each bounded implementation task.

Poll GitHub every 15 seconds. A sidecar adds the required `symphony` label and a durable `symphony-dispatched` marker only to issues whose author association is owner, member, or collaborator.

Use Symphony's host-side `github_api` tool for issue and pull request operations. Use a separate SSH-agent container for Git pushes. Do not mount the GitHub deploy key into the orchestrator.

## Rationale

GitHub-hosted runners cannot use a persistent ChatGPT Plus login safely. Spark provides the persistent trusted machine that the advanced Codex authentication flow requires.

The main session performs coordination and final repository work, so Luna is the default. Planning and progress review are bounded, read-only tasks, so custom Astra agents give those tasks the requested model. The planner selects Qwen only for bounded implementation work that fits the local model.

The label gate prevents unknown public users from consuming the subscription. The dispatch marker prevents finished issues from entering an automatic retry loop. Separate token, key, and model-process boundaries reduce credential exposure if issue text or repository content is hostile.

## Consequences

Spark must remain online and Docker must restart the stack after a host reboot.

The ChatGPT login is a renewable credential. Operators must protect its state directory and reauthenticate when the session expires. Only one issue runs at a time to avoid concurrent issue work and workspace claims. A single issue can use several subagent threads, but workers must own disjoint files and the primary agent must review the combined diff.

The GitHub token can read and write repository issues and pull requests. Symphony keeps it out of the Codex child process, but the host-side `github_api` tool can use all permissions granted to that token.

The official Symphony implementation is prototype software. The deployment therefore isolates workspaces, drops Linux capabilities, binds the dashboard to loopback, gates issue authors, and keeps raw credentials outside the agent container where practical. Codex uses its documented `externalSandbox` mode because Docker supplies the process boundary and the hardened container does not permit the namespaces required by Codex's inner Linux sandbox.

## Local Qwen profile

The Spark deployment downloads `Qwen/Qwen3.8-27B` in a labeled `qwen-init` container, then runs the model in a dedicated vLLM container. The inference container uses the private `airi-symphony-model` network and exposes no host port. The orchestrator reaches the model through `http://qwen:8000/v1`.

The Qwen service uses a pinned ARM64 vLLM image, a 65,536-token context limit, one request sequence, a 64 GiB memory limit, and no swap allowance. The Compose service has the `owner: sephy` label. Model weights and vLLM cache data remain in named Docker volumes.

Codex loads the provider from `config.toml` and the explicit `spark-qwen` profile. The planner can route bounded implementation work to the Qwen custom agent. The profile does not change Symphony's Astra planning or Luna primary-coordination routes. All model download and inference commands run inside Docker containers.

## References

- [OpenAI Symphony](https://github.com/openai/symphony)
- [Symphony Elixir runtime](https://github.com/openai/symphony/tree/main/elixir)
- [Codex authentication](https://learn.chatgpt.com/docs/auth)
- [Codex CI/CD authentication](https://learn.chatgpt.com/docs/auth/ci-cd-auth)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
