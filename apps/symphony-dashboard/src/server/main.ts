import process from 'node:process'

import { serve } from '@hono/node-server'
import { serveStatic } from '@hono/node-server/serve-static'

import { createDashboardApp } from './app'
import { createHistoryRepository } from './history'
import { createRuntimeSource } from './source'

const port = Number.parseInt(process.env.SYMPHONY_DASHBOARD_PORT ?? '4177', 10)
const hostname = process.env.SYMPHONY_DASHBOARD_HOST ?? '127.0.0.1'
const deploymentId = process.env.SYMPHONY_DEPLOYMENT_ID ?? 'symphony-spark-container'
const runtimeUrl = process.env.SYMPHONY_RUNTIME_URL ?? 'http://127.0.0.1:8000'
const historyPath = process.env.SYMPHONY_DASHBOARD_HISTORY_PATH ?? './data'

const app = createDashboardApp({
  deploymentId,
  source: createRuntimeSource({ baseUrl: runtimeUrl }),
  history: createHistoryRepository({ basePath: historyPath }),
  allowedLinkHosts: (process.env.SYMPHONY_TRACKER_HOSTS ?? 'github.com').split(',').map(host => host.trim()).filter(Boolean),
})

app.use('/*', serveStatic({ root: './dist' }))
app.get('*', serveStatic({ path: './dist/index.html' }))

serve({ fetch: app.fetch, hostname, port })
