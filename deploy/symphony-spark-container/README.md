# Symphony Spark dashboard deployment

This directory documents the additive dashboard service for the Symphony Spark
container. The service does not replace the Symphony runner or its health
endpoint.

## Start

Run these commands from the repository root:

```bash
pnpm install
pnpm -F @proj-airi/symphony-dashboard build
pnpm -F @proj-airi/symphony-dashboard start
```

Set `SYMPHONY_RUNTIME_URL` to the internal Symphony runtime URL. Set
`SYMPHONY_DASHBOARD_HISTORY_PATH` to a persistent volume.

## Access

Route the existing authenticated Spark dashboard tunnel to the dashboard port.
Keep the current runner and health route on their current routes. Do not expose
the dashboard port directly to the public network.

The current checkout does not contain the Spark container manifest or tunnel
configuration. A deployment owner must add those routes before production use.

## Refresh and history

The dashboard reads runtime state without changing tracker or orchestrator
state. It polls every five seconds after a successful read.

The server stores sanitized cards and events in the history path. A card remains
visible when it disappears from a later runtime snapshot. The card then shows a
stale state. The server never treats disappearance as verification.

## Privacy

The server sends only the public dashboard contract to the browser. It removes
private reasoning, prompts, transcripts, tool data, credentials, cookies, raw
tokens, and raw error payloads before persistence or delivery.

Keep the Spark tunnel authentication, runtime origin, and history volume
private. Do not write runtime responses to logs.

## Integration gap

This repository has no Symphony runner, deployment manifest, runtime schema, or
`WORKFLOW.md`. The dashboard includes a deterministic fixture and an adapter for
`/api/v1/state` and per-task endpoints. Production acceptance requires a real
runtime lifecycle, durable history after restart, unchanged health behavior,
continued runner operation, and authenticated tunnel access.
