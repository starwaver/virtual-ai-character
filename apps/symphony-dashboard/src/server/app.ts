import type { DashboardSnapshot } from '../shared/task'
import type { HistoryRepository } from './history'
import type { RuntimeSource } from './source'

import { Hono } from 'hono'

import { historySnapshot, mergeSnapshot } from './history'
import { InvalidRuntimeStateError, normalizeRuntimeState } from './normalize'
import { RuntimeSourceError } from './source'

interface DashboardAppOptions {
  deploymentId: string
  source: RuntimeSource
  history: HistoryRepository
  clock?: () => string
  allowedLinkHosts?: readonly string[]
}

function errorCode(error: unknown): DashboardSnapshot['sourceErrorCode'] {
  if (error instanceof RuntimeSourceError)
    return error.code
  if (error instanceof InvalidRuntimeStateError)
    return error.code
  return 'unavailable'
}

function responseStatus(snapshot: DashboardSnapshot): 200 | 502 {
  return snapshot.sourceStatus === 'ok' || snapshot.tasks.length > 0 ? 200 : 502
}

/**
 * Creates the read-only dashboard API.
 *
 * The app reads the runtime through one configured source, filters it before
 * persistence, and never exposes a route that mutates Symphony state.
 */
export function createDashboardApp(options: DashboardAppOptions): Hono {
  const clock = options.clock ?? (() => new Date().toISOString())
  const app = new Hono()

  app.get('/healthz', c => c.json({ status: 'ok', readOnly: true }))

  app.get('/api/dashboard/state', async (c) => {
    const observedAt = clock()
    const history = await options.history.load()

    try {
      const runtimeState = await options.source.readState()
      const snapshot = normalizeRuntimeState(runtimeState, {
        deploymentId: options.deploymentId,
        observedAt,
        allowedLinkHosts: options.allowedLinkHosts,
      })
      const nextHistory = mergeSnapshot(history, snapshot)
      await options.history.save(nextHistory)
      return c.json(historySnapshot(nextHistory, observedAt, 'ok', null))
    }
    catch (error) {
      const snapshot = historySnapshot(history, observedAt, error instanceof RuntimeSourceError && error.code === 'unsupported' ? 'unsupported' : 'error', errorCode(error))
      return c.json(snapshot, responseStatus(snapshot))
    }
  })

  app.get('/api/dashboard/tasks/:taskKey', async (c) => {
    const taskKey = c.req.param('taskKey')
    const history = await options.history.load()
    const previous = history.tasks.find(task => task.key === taskKey)
    if (!previous)
      return c.json({ error: 'not_found' }, 404)

    try {
      const runtimeState = await options.source.readTask(taskKey)
      const snapshot = normalizeRuntimeState({ tasks: [runtimeState] }, {
        deploymentId: options.deploymentId,
        observedAt: clock(),
        allowedLinkHosts: options.allowedLinkHosts,
      })
      const nextHistory = mergeSnapshot(history, snapshot)
      await options.history.save(nextHistory)
      return c.json(nextHistory.tasks.find(task => task.key === taskKey) ?? previous)
    }
    catch {
      return c.json(previous)
    }
  })

  return app
}
