import type { DashboardHistory } from '../shared/task'

import { describe, expect, it } from 'vitest'

import { createDashboardApp } from './app'

describe('createDashboardApp', () => {
  // https://github.com/starwaver/virtual-ai-character/issues/5
  it('serves sanitized state and keeps the API read-only', async () => {
    const observedAt = '2026-09-23T01:00:00.000Z'
    const runtimeState = {
      tasks: [{
        id: '5',
        title: 'Build the board',
        status: 'doing',
        progressSummary: 'Public progress',
        privateReasoning: 'Do not expose this reasoning.',
        events: [{ type: 'progress', publicSummary: 'The adapter is ready.', observedAt }],
      }],
    }
    let history: DashboardHistory = {
      schemaVersion: 1,
      deploymentId: 'fixture',
      lastSuccessfulSourceAt: null,
      tasks: [],
    }
    const app = createDashboardApp({
      deploymentId: 'fixture',
      source: {
        readState: async () => runtimeState,
        readTask: async () => runtimeState.tasks[0],
      },
      history: {
        load: async () => history,
        save: async (next) => { history = next },
      },
      clock: () => observedAt,
    })

    const response = await app.request('/api/dashboard/state')
    const body = await response.text()

    expect(response.status).toBe(200)
    expect(body).toContain('Public progress')
    expect(body).not.toContain('private reasoning')

    const mutation = await app.request('/api/dashboard/state', { method: 'POST' })
    expect(mutation.status).toBe(404)
  })
})
