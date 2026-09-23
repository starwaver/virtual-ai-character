# Symphony dashboard

This workspace contains the read-only dashboard and its runtime adapter.

The adapter reads `GET /api/v1/state` from the configured Symphony runtime. It
keeps only the public task fields that the dashboard contract names. It stores
the sanitized task history in the configured dashboard data path.

## Start the dashboard

Install the workspace dependencies from the repository root.

```bash
pnpm install
pnpm -F @proj-airi/symphony-dashboard dev
```

Use `pnpm -F @proj-airi/symphony-dashboard start` after a production build.
The server listens on `127.0.0.1:4177` by default.

Set these environment values before you start the server:

| Name | Default | Purpose |
| --- | --- | --- |
| `SYMPHONY_RUNTIME_URL` | `http://127.0.0.1:8000` | Read-only Symphony origin |
| `SYMPHONY_DASHBOARD_PORT` | `4177` | Dashboard port |
| `SYMPHONY_DASHBOARD_HOST` | `127.0.0.1` | Dashboard bind address |
| `SYMPHONY_DEPLOYMENT_ID` | `symphony-spark-container` | History namespace |
| `SYMPHONY_DASHBOARD_HISTORY_PATH` | `./data` | Persistent history path |
| `SYMPHONY_TRACKER_HOSTS` | `github.com` | Allowed issue and PR hosts |

## Access and refresh

Open the dashboard through the existing authenticated Spark tunnel. The
dashboard uses the same origin for browser requests.

The browser refreshes the state every five seconds after a successful read.
It doubles the delay after an error and stops at sixty seconds. It stops while
the tab is hidden and refreshes when the tab becomes visible.

The dashboard reads `/api/dashboard/state` and task detail endpoints. It does
not provide controls to retry, cancel, approve, or change a task.

## Privacy

The server filters runtime data before it sends or stores the data. It does not
send prompts, private reasoning, transcripts, tool payloads, cookies, tokens,
credentials, environment data, or raw response bodies to the browser.

Progress text must come from the runtime's explicit public progress field. The
dashboard does not create a summary from private messages.

Keep the tunnel authentication and the dashboard history path private. The
dashboard is an operations view, not a public status page.

## Runtime contract status

This repository does not contain the `symphony-spark-container` runner,
deployment manifest, tunnel configuration, or a `WORKFLOW.md` file. The adapter
therefore uses the documented endpoint names and a deterministic fixture
contract until those deployment files are available.

Before production access, connect the adapter to the real runtime contract.
Confirm the task identity, attempt identity, public progress field, lifecycle
events, durable history source, health route, and tunnel access policy.

The adapter keeps missing tasks as stale cards. A transient state endpoint alone
cannot prove that a task completed before the dashboard observed it.
